"""Production prediction layer.

This is the file the Streamlit app imports. It tries to use the trained
XGBoost model. If no model exists (model not yet trained), falls back to
the deterministic stub predictions so the UI doesn't break.

Same dataclass signatures as predict_stub — fully drop-in.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import text as sql_text

from ..db.session import get_session
from ..ml.features import build_match_features, get_cached_features
from ..ml.model import load_model, predict_match_proba
from .predict_stub import LossAnalysis, MapPrediction, MatchPrediction

log = logging.getLogger(__name__)


_VALORANT_MAP_POOL = [
    "Abyss", "Ascent", "Bind", "Fracture", "Haven", "Lotus", "Pearl", "Split", "Sunset"
]


def _stable_hash(*parts: str) -> float:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _confidence_label(prob_a: float) -> str:
    margin = abs(prob_a - 0.5)
    if margin > 0.15: return "high"
    if margin > 0.07: return "medium"
    return "low"


def _build_features_for_teams(team_a_id: Optional[int], team_b_id: Optional[int]) -> Optional[dict]:
    """Build live features for a hypothetical match between two teams *right now*.

    Uses each team's most recent lineup (5 players from their last match)
    and computes features as_of today.
    """
    if team_a_id is None or team_b_id is None:
        return None

    session = get_session()
    try:
        # Find most recent match for each team
        def _latest_lineup(tid):
            row = session.execute(sql_text("""
                SELECT m.id, m.match_datetime
                FROM matches m
                WHERE (m.team_a_id = :tid OR m.team_b_id = :tid)
                  AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
                ORDER BY m.match_datetime DESC NULLS LAST
                LIMIT 1
            """), {"tid": tid}).first()
            if row is None:
                return None, None
            match_id = row[0]
            players = session.execute(sql_text("""
                SELECT DISTINCT player_id FROM player_map_stats
                WHERE match_id = :mid AND team_id = :tid
                LIMIT 5
            """), {"mid": match_id, "tid": tid}).all()
            return [p[0] for p in players], row[1]

        lineup_a, last_a = _latest_lineup(team_a_id)
        lineup_b, last_b = _latest_lineup(team_b_id)

        if not lineup_a or not lineup_b:
            return None

        from ..ml.features import build_team_features
        # "As of now" — use today as the cutoff
        as_of = datetime.utcnow()
        team_a_feats = build_team_features(session, lineup_a, as_of)
        team_b_feats = build_team_features(session, lineup_b, as_of)

        features = {}
        features.update(team_a_feats.to_dict(prefix="team_a_"))
        features.update(team_b_feats.to_dict(prefix="team_b_"))

        a_dict = team_a_feats.to_dict(prefix="")
        b_dict = team_b_feats.to_dict(prefix="")
        for key in a_dict:
            features[f"diff_{key}"] = a_dict[key] - b_dict[key]
        return features
    finally:
        session.close()


def predict_match(
    team_a_name: str,
    team_b_name: str,
    team_a_id: Optional[int] = None,
    team_b_id: Optional[int] = None,
    best_of: int = 3,
) -> MatchPrediction:
    """Real prediction. Falls back to stub if model not yet trained."""
    bundle = load_model()
    if bundle is None or team_a_id is None or team_b_id is None:
        return _stub_predict(team_a_name, team_b_name, best_of)

    features = _build_features_for_teams(team_a_id, team_b_id)
    if features is None:
        return _stub_predict(team_a_name, team_b_name, best_of)

    result = predict_match_proba(features, best_of=best_of)
    if result is None:
        return _stub_predict(team_a_name, team_b_name, best_of)

    # Per-map predictions: re-use the per-map probability for now
    # (a future improvement would condition per-map prob on the map name)
    p_map = result["per_map_prob_a"]
    map_picks = []
    for map_name in _VALORANT_MAP_POOL[:5]:
        # Small deterministic per-map variation to make the UI interesting
        variation = (_stable_hash(team_a_name, team_b_name, map_name) - 0.5) * 0.08
        map_p_a = max(0.15, min(0.85, p_map + variation))
        map_picks.append(MapPrediction(
            map_name=map_name,
            prob_a=round(map_p_a, 3),
            prob_b=round(1 - map_p_a, 3),
            confidence=_confidence_label(map_p_a),
        ))

    # Cross-tier warning. avg_recent_opp_tier is on a 1-3 scale
    # (1=tier2/Challengers, 2=tier1/regional, 3=international).
    # Flag matchups where the gap is > 1.0 — that's roughly "Challengers
    # team meeting an international-tier team" territory.
    cross_warning = _compute_cross_tier_warning(
        features.get("team_a_avg_recent_opp_tier", 0.0),
        features.get("team_b_avg_recent_opp_tier", 0.0),
        team_a_name, team_b_name,
    )

    return MatchPrediction(
        team_a_name=team_a_name,
        team_b_name=team_b_name,
        prob_a=round(result["prob_a"], 3),
        prob_b=round(result["prob_b"], 3),
        predicted_score_a=result["predicted_score_a"],
        predicted_score_b=result["predicted_score_b"],
        best_of=best_of,
        map_predictions=map_picks,
        confidence=_confidence_label(result["prob_a"]),
        note=f"XGBoost prediction (model v1) · tier-aware features",
        cross_tier_warning=cross_warning,
    )


_TIER_LABELS = {3: "International", 2: "Tier 1 Regional", 1: "Tier 2 / Challengers"}


def _compute_cross_tier_warning(
    a_opp_tier: float, b_opp_tier: float,
    a_name: str, b_name: str,
) -> Optional[str]:
    """Return a plain-text warning if the two teams have very different
    recent opponent-tier histories. None if they're well-matched."""
    if a_opp_tier <= 0.0 or b_opp_tier <= 0.0:
        # One or both teams have no recent tier-classified matches
        return None
    gap = abs(a_opp_tier - b_opp_tier)
    if gap < 0.75:
        return None  # well-matched, no warning needed

    def _label(t: float) -> str:
        if t >= 2.5: return "International"
        if t >= 1.5: return "Tier 1 Regional"
        return "Tier 2 / Challengers"

    stronger = a_name if a_opp_tier > b_opp_tier else b_name
    weaker = b_name if a_opp_tier > b_opp_tier else a_name
    stronger_tier = _label(max(a_opp_tier, b_opp_tier))
    weaker_tier = _label(min(a_opp_tier, b_opp_tier))

    return (
        f"Cross-tier matchup. {stronger} has been playing {stronger_tier} "
        f"opposition recently; {weaker} has been playing {weaker_tier}. "
        "Predictions for cross-tier matchups have elevated uncertainty."
    )


def predict_fantasy(
    team_a_players: list[str],
    team_b_players: list[str],
    best_of: int = 3,
) -> MatchPrediction:
    """Fantasy prediction. Requires the real model — falls back to stub otherwise.

    Resolves player names to ids, builds team features from those exact
    rosters, and runs the model.
    """
    bundle = load_model()
    if bundle is None:
        return _stub_predict("Custom Team A", "Custom Team B", best_of)

    session = get_session()
    try:
        def _resolve_ids(names):
            ids = []
            for name in names:
                row = session.execute(sql_text(
                    "SELECT id FROM players WHERE name = :n LIMIT 1"
                ), {"n": name}).first()
                if row:
                    ids.append(row[0])
            return ids

        ids_a = _resolve_ids(team_a_players)
        ids_b = _resolve_ids(team_b_players)
        if len(ids_a) < 5 or len(ids_b) < 5:
            return _stub_predict("Custom Team A", "Custom Team B", best_of)

        from ..ml.features import build_team_features
        as_of = datetime.utcnow()
        team_a_feats = build_team_features(session, ids_a, as_of)
        team_b_feats = build_team_features(session, ids_b, as_of)
    finally:
        session.close()

    features = {}
    features.update(team_a_feats.to_dict(prefix="team_a_"))
    features.update(team_b_feats.to_dict(prefix="team_b_"))
    a_dict = team_a_feats.to_dict(prefix="")
    b_dict = team_b_feats.to_dict(prefix="")
    for key in a_dict:
        features[f"diff_{key}"] = a_dict[key] - b_dict[key]

    result = predict_match_proba(features, best_of=best_of)
    if result is None:
        return _stub_predict("Custom Team A", "Custom Team B", best_of)

    p_map = result["per_map_prob_a"]
    map_picks = []
    for map_name in _VALORANT_MAP_POOL[:5]:
        variation = (_stable_hash("custom_a", "custom_b", map_name) - 0.5) * 0.08
        map_p_a = max(0.15, min(0.85, p_map + variation))
        map_picks.append(MapPrediction(
            map_name=map_name,
            prob_a=round(map_p_a, 3),
            prob_b=round(1 - map_p_a, 3),
            confidence=_confidence_label(map_p_a),
        ))

    return MatchPrediction(
        team_a_name="Custom Team A",
        team_b_name="Custom Team B",
        prob_a=round(result["prob_a"], 3),
        prob_b=round(result["prob_b"], 3),
        predicted_score_a=result["predicted_score_a"],
        predicted_score_b=result["predicted_score_b"],
        best_of=best_of,
        map_predictions=map_picks,
        confidence=_confidence_label(result["prob_a"]),
        note="XGBoost prediction (model v1) on custom roster",
    )


def explain_loss(match_id: int, team_lost: str, team_won: str) -> LossAnalysis:
    """Real LLM-backed loss analysis.

    Calls OpenAI through `vlr.ml.explain.explain_match()`. If the API key
    isn't configured or the call fails, falls back to the placeholder
    text from `predict_stub` so the UI doesn't break.
    """
    try:
        from ..ml.explain import explain_match
        result = explain_match(match_id, force_regenerate=False)
        if result is not None:
            return result
    except Exception:
        log.exception("LLM explanation failed for match %d — falling back to stub", match_id)

    from .predict_stub import explain_loss as stub_explain
    return stub_explain(match_id, team_lost, team_won)


def explain_loss_regenerate(match_id: int, team_lost: str, team_won: str) -> LossAnalysis:
    """Like explain_loss but forces a fresh OpenAI call (ignores cache)."""
    try:
        from ..ml.explain import explain_match
        result = explain_match(match_id, force_regenerate=True)
        if result is not None:
            return result
    except Exception:
        log.exception("Regenerate LLM explanation failed for match %d", match_id)

    from .predict_stub import explain_loss as stub_explain
    return stub_explain(match_id, team_lost, team_won)


# --- Stub fallback --------------------------------------------------------


def _stub_predict(team_a_name: str, team_b_name: str, best_of: int) -> MatchPrediction:
    """Stub fallback when the real model can't be loaded or features can't be built."""
    from .predict_stub import predict_match as stub_predict
    result = stub_predict(team_a_name, team_b_name, best_of=best_of)
    result.note = "Placeholder prediction — model not yet trained or features unavailable"
    return result
