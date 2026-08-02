"""OpenAI-powered match analysis.

The flow:
1. Pull the match's per-player stats, scoreboard, and event context from the DB
2. Pull the model's prediction + SHAP attribution for that match
3. Build a structured prompt with all of this
4. Call the OpenAI API
5. Parse the response into a structured LossAnalysis dataclass
6. Cache the result in match_analysis_cache

The LLM doesn't compute or compare numbers. It takes our deterministic
numerical facts (stats, model attribution) and turns them into prose.
This is the "ML identifies influential factors, GenAI verbalizes them"
methodology your critical review proposed.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from ..config import settings
from ..db.session import get_session

log = logging.getLogger(__name__)

PROMPT_VERSION = "v1"


# Local re-declaration of LossAnalysis to avoid a cross-package import
# (and the circular risk that comes with it). Schema is the same as
# `vlr.app.predict_stub.LossAnalysis` — callers can use either, they're
# structurally interchangeable.
@dataclass
class LossAnalysis:
    summary: str
    key_factors: list[str]
    standout_players: list[str]
    underperformers: list[str]


# --- Public API ----------------------------------------------------------


def explain_match(
    match_id: int,
    force_regenerate: bool = False,
) -> Optional[LossAnalysis]:
    """Generate (or retrieve cached) LLM analysis for a match.

    Returns None if the OpenAI API isn't configured. Caller should fall
    back to the stub explanation in that case.
    """
    if not settings.openai_api_key:
        log.warning("OPENAI_API_KEY not set — skipping LLM call")
        return None

    session = get_session()
    try:
        if not force_regenerate:
            cached = _load_cached(session, match_id)
            if cached is not None:
                return cached

        match_context = _build_match_context(session, match_id)
        if match_context is None:
            log.warning("Could not build context for match %d", match_id)
            return None

        analysis = _call_openai(match_context)
        if analysis is None:
            return None

        _save_cached(session, match_id, analysis)
        return analysis
    finally:
        session.close()


# --- Cache helpers -------------------------------------------------------


def _load_cached(session: Session, match_id: int) -> Optional[LossAnalysis]:
    row = session.execute(sql_text("""
        SELECT analysis, prompt_version FROM match_analysis_cache
        WHERE match_id = :mid
    """), {"mid": match_id}).first()
    if row is None:
        return None
    if row[1] != PROMPT_VERSION:
        # Prompt was updated — stale cache, ignore it
        return None
    data = json.loads(row[0]) if isinstance(row[0], str) else dict(row[0])
    return LossAnalysis(
        summary=data["summary"],
        key_factors=data["key_factors"],
        standout_players=data["standout_players"],
        underperformers=data["underperformers"],
    )


def _save_cached(session: Session, match_id: int, analysis: LossAnalysis) -> None:
    session.execute(sql_text("""
        INSERT INTO match_analysis_cache (match_id, analysis, model, prompt_version, generated_at)
        VALUES (:mid, :analysis, :model, :prompt_version, NOW())
        ON CONFLICT (match_id) DO UPDATE
            SET analysis = EXCLUDED.analysis,
                model = EXCLUDED.model,
                prompt_version = EXCLUDED.prompt_version,
                generated_at = NOW()
    """), {
        "mid": match_id,
        "analysis": json.dumps(asdict(analysis)),
        "model": settings.openai_model,
        "prompt_version": PROMPT_VERSION,
    })
    session.commit()


# --- Context assembly ----------------------------------------------------


def _build_match_context(session: Session, match_id: int) -> Optional[dict]:
    """Pull every piece of structured data the LLM needs."""
    # Lazy imports — keep top-level imports lean to avoid any circular paths
    from .attribution import attribute_prediction, humanize_feature
    from .features import get_cached_features

    # Match metadata
    match_row = session.execute(sql_text("""
        SELECT m.id, m.team_a_name, m.team_b_name, m.score_a, m.score_b,
               m.best_of, m.stage, m.patch, m.match_datetime,
               e.name AS event_name, e.tier AS event_tier
        FROM matches m
        LEFT JOIN events e ON e.id = m.event_id
        WHERE m.id = :mid
    """), {"mid": match_id}).first()
    if match_row is None:
        return None

    # Per-map results
    map_rows = session.execute(sql_text("""
        SELECT id, map_index, map_name, score_a, score_b, picked_by
        FROM maps_played
        WHERE match_id = :mid
        ORDER BY map_index
    """), {"mid": match_id}).all()

    maps = []
    for m in map_rows:
        # Per-player stats for this map
        player_rows = session.execute(sql_text("""
            SELECT p.name, pms.team_name, pms.agent, pms.rating, pms.acs,
                   pms.kills, pms.deaths, pms.assists, pms.kast, pms.adr
            FROM player_map_stats pms
            JOIN players p ON p.id = pms.player_id
            WHERE pms.map_id = :map_id AND pms.rating IS NOT NULL
            ORDER BY pms.team_name, pms.rating DESC NULLS LAST
        """), {"map_id": m[0]}).all()

        maps.append({
            "index": m[1],
            "name": m[2],
            "score_a": m[3],
            "score_b": m[4],
            "picked_by": m[5],
            "players": [
                {
                    "name": p[0], "team": p[1], "agent": p[2],
                    "rating": float(p[3]) if p[3] else None,
                    "acs": p[4], "kills": p[5], "deaths": p[6], "assists": p[7],
                    "kast": p[8], "adr": float(p[9]) if p[9] else None,
                }
                for p in player_rows
            ],
        })

    # Model prediction + SHAP attribution (if features are available)
    features = get_cached_features(session, match_id)
    attribution = None
    if features is not None:
        attribution = attribute_prediction(features)

    # Top influential features formatted for the prompt
    top_features = []
    if attribution is not None:
        for attr in attribution.top(8):
            top_features.append({
                "label": humanize_feature(attr.feature),
                "raw_name": attr.feature,
                "value": round(attr.value, 3),
                "shap": round(attr.shap_value, 4),
                "favors": "team_a" if attr.shap_value > 0 else "team_b",
            })

    # Determine if this was an upset (vs model prediction)
    a_won = match_row[3] > match_row[4]
    upset = False
    if attribution is not None:
        # If model favored team B but A won, or vice versa → upset
        model_favored_a = attribution.prediction > 0
        upset = (a_won and not model_favored_a) or (not a_won and model_favored_a)

    return {
        "match_id": match_id,
        "team_a_name": match_row[1],
        "team_b_name": match_row[2],
        "score_a": match_row[3],
        "score_b": match_row[4],
        "winner": match_row[1] if a_won else match_row[2],
        "loser": match_row[2] if a_won else match_row[1],
        "best_of": match_row[5],
        "stage": match_row[6],
        "patch": match_row[7],
        "datetime": match_row[8].isoformat() if match_row[8] else None,
        "event_name": match_row[9],
        "event_tier": match_row[10],
        "maps": maps,
        "top_features": top_features,
        "model_predicted_prob_a": (
            float(1 / (1 + 2.71828 ** (-attribution.prediction))) if attribution else None
        ),
        "is_upset": upset,
    }


# --- Prompt construction --------------------------------------------------


_SYSTEM_PROMPT = """You are an expert Valorant esports analyst writing for a coaching audience.

You analyze completed professional matches and produce structured, evidence-based commentary. Your style is concise, technical, and grounded — coaches use this to debrief.

Strict rules:
- Use ONLY the numerical facts provided in the user message. Do not invent stats.
- When you mention a player or team, ALWAYS back it with a specific number from the data.
- Be neutral and analytical, not sensational. No "incredible", "unbelievable", "shocking".
- Reference the ML model's attributions when explaining why the outcome happened.
- Keep the summary to 3-4 sentences. Each list item should be one sentence.

Output format: a single JSON object with exactly these keys:
{
  "summary": "3-4 sentence overview of what happened and why",
  "key_factors": ["factor 1", "factor 2", "factor 3", "factor 4"],
  "standout_players": ["1-2 standout performers with specific stats"],
  "underperformers": ["1-2 players who struggled with specific stats"]
}

Return ONLY the JSON, no preamble or markdown."""


def _build_user_prompt(ctx: dict) -> str:
    """Construct the per-match user prompt from the structured context."""
    parts = []

    # Match header
    framing = "an upset" if ctx["is_upset"] else "the expected outcome"
    parts.append(
        f"Match: {ctx['team_a_name']} vs {ctx['team_b_name']}\n"
        f"Score: {ctx['team_a_name']} {ctx['score_a']}–{ctx['score_b']} {ctx['team_b_name']} "
        f"({ctx['winner']} won)\n"
        f"Event: {ctx['event_name'] or 'Unknown'} "
        f"({ctx['event_tier'] or 'unclassified tier'})\n"
        f"Stage: {ctx['stage'] or 'Unknown'} · Best of {ctx['best_of'] or '?'}\n"
        f"This result was {framing} according to our predictive model.\n"
    )

    # Per-map summary
    parts.append("\nMap-by-map:")
    for m in ctx["maps"]:
        parts.append(
            f"- Map {m['index']} ({m['name']}): "
            f"{ctx['team_a_name']} {m['score_a']}–{m['score_b']} {ctx['team_b_name']}"
            + (f"  [picked by {m['picked_by']}]" if m["picked_by"] else "")
        )

    # Player stats across the series, aggregated
    if any(m["players"] for m in ctx["maps"]):
        parts.append("\nPlayer performances (per-map averages across the series):")
        # Aggregate across maps
        player_agg: dict[str, dict] = {}
        for m in ctx["maps"]:
            for p in m["players"]:
                key = (p["name"], p["team"])
                if key not in player_agg:
                    player_agg[key] = {
                        "name": p["name"], "team": p["team"],
                        "ratings": [], "acss": [], "kasts": [], "adrs": [],
                        "agents": set(),
                    }
                if p["rating"] is not None:
                    player_agg[key]["ratings"].append(p["rating"])
                if p["acs"] is not None:
                    player_agg[key]["acss"].append(p["acs"])
                if p["kast"] is not None:
                    player_agg[key]["kasts"].append(p["kast"])
                if p["adr"] is not None:
                    player_agg[key]["adrs"].append(p["adr"])
                if p["agent"]:
                    player_agg[key]["agents"].add(p["agent"])

        # Sort by average rating
        sorted_players = sorted(
            player_agg.values(),
            key=lambda x: sum(x["ratings"]) / len(x["ratings"]) if x["ratings"] else 0,
            reverse=True,
        )
        for p in sorted_players:
            if not p["ratings"]:
                continue
            avg_rating = sum(p["ratings"]) / len(p["ratings"])
            avg_acs = sum(p["acss"]) / len(p["acss"]) if p["acss"] else 0
            avg_kast = sum(p["kasts"]) / len(p["kasts"]) if p["kasts"] else 0
            avg_adr = sum(p["adrs"]) / len(p["adrs"]) if p["adrs"] else 0
            agents = ", ".join(sorted(p["agents"]))
            parts.append(
                f"- {p['name']} ({p['team']}, played {agents}): "
                f"avg rating {avg_rating:.2f}, ACS {avg_acs:.0f}, "
                f"KAST {avg_kast:.0f}%, ADR {avg_adr:.1f}"
            )

    # ML attribution
    if ctx["top_features"]:
        parts.append(
            f"\nML model attribution (this is what our XGBoost model identified as "
            f"most influential for predicting the outcome):"
        )
        for tf in ctx["top_features"]:
            direction = "favored " + (
                ctx["team_a_name"] if tf["favors"] == "team_a" else ctx["team_b_name"]
            )
            parts.append(
                f"- {tf['label']}: value={tf['value']}, "
                f"SHAP impact={tf['shap']:+.3f} ({direction})"
            )
        if ctx["model_predicted_prob_a"] is not None:
            parts.append(
                f"\nThe model predicted P({ctx['team_a_name']} wins) = "
                f"{ctx['model_predicted_prob_a']:.2%} before the match."
            )

    parts.append(
        f"\nTask: Generate the structured JSON analysis as specified in the system prompt. "
        f"Focus on {ctx['loser']}'s loss — what went wrong, who underperformed, "
        f"and how does the ML attribution help explain it. Reference the model's "
        f"attribution naturally where it adds insight."
    )

    return "\n".join(parts)


# --- OpenAI call ----------------------------------------------------------


def _call_openai(context: dict) -> Optional[LossAnalysis]:
    """Make the API call and parse the JSON response."""
    try:
        from openai import OpenAI
    except ImportError:
        log.error(
            "openai package not installed. Run `pip install openai`."
        )
        return None

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )

    user_prompt = _build_user_prompt(context)
    log.debug("OpenAI prompt:\n%s", user_prompt)

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
    except Exception:
        log.exception("OpenAI call failed for match %s", context.get("match_id"))
        return None

    raw_content = response.choices[0].message.content
    if not raw_content:
        log.warning("OpenAI returned empty content")
        return None

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        log.exception("Could not parse OpenAI response as JSON: %s", raw_content[:500])
        return None

    # Validate shape — graceful fallback if any key is missing
    return LossAnalysis(
        summary=data.get("summary", "")[:2000] or "Analysis unavailable.",
        key_factors=list(data.get("key_factors", []))[:8],
        standout_players=list(data.get("standout_players", []))[:5],
        underperformers=list(data.get("underperformers", []))[:5],
    )
