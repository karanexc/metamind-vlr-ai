"""Placeholder prediction layer.

Every function here returns a deterministic but plausible fake result.
The UI is wired to these signatures so when we ship the real model
in a later iteration, only this file needs to change.

The randomness is seeded by inputs so predictions are stable across
page refreshes (a real model would behave the same way).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class MapPrediction:
    map_name: str
    prob_a: float
    prob_b: float
    confidence: str  # "high" / "medium" / "low"


@dataclass
class MatchPrediction:
    team_a_name: str
    team_b_name: str
    prob_a: float
    prob_b: float
    predicted_score_a: int
    predicted_score_b: int
    best_of: int
    map_predictions: list[MapPrediction]
    confidence: str
    note: str  # e.g. "Based on last 30 days of form"
    # Set when the two teams have very different opponent-tier histories.
    # Plain-text warning the UI surfaces, or None when not applicable.
    cross_tier_warning: Optional[str] = None


def _stable_hash(*parts: str) -> float:
    """Hash inputs to a float in [0, 1] for stable fake-prediction values."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    # Take first 8 hex chars as int, normalize
    return int(h[:8], 16) / 0xFFFFFFFF


_VALORANT_MAP_POOL = [
    "Abyss", "Ascent", "Bind", "Fracture", "Haven", "Lotus", "Pearl", "Split", "Sunset"
]


def predict_match(
    team_a_name: str,
    team_b_name: str,
    team_a_id: Optional[int] = None,
    team_b_id: Optional[int] = None,
    best_of: int = 3,
) -> MatchPrediction:
    """Stub prediction. Returns a deterministic but plausible result.

    When the real model lands, this function's signature stays the same —
    only the implementation changes.
    """
    # Deterministic 'win probability' based on team names
    raw = _stable_hash(team_a_name, team_b_name)
    # Skew toward neutral (0.35–0.65 range) so predictions look reasonable
    prob_a = 0.35 + raw * 0.30

    # If raw was below 0.5, swap so team B wins instead — gives variety
    if raw > 0.5:
        prob_a = 1 - prob_a
    prob_b = 1 - prob_a

    # Score prediction
    wins_needed = (best_of + 1) // 2
    if prob_a > 0.5:
        predicted_score_a = wins_needed
        predicted_score_b = max(0, wins_needed - 1 - int((prob_a - 0.5) * 2))
    else:
        predicted_score_b = wins_needed
        predicted_score_a = max(0, wins_needed - 1 - int((prob_b - 0.5) * 2))

    # Per-map predictions (pick 5 maps from the pool deterministically)
    map_picks = []
    for i, map_name in enumerate(_VALORANT_MAP_POOL[:5]):
        map_raw = _stable_hash(team_a_name, team_b_name, map_name)
        map_prob_a = 0.30 + map_raw * 0.40
        confidence = "high" if abs(map_prob_a - 0.5) > 0.15 else ("medium" if abs(map_prob_a - 0.5) > 0.05 else "low")
        map_picks.append(MapPrediction(
            map_name=map_name,
            prob_a=round(map_prob_a, 3),
            prob_b=round(1 - map_prob_a, 3),
            confidence=confidence,
        ))

    overall_confidence = "high" if abs(prob_a - 0.5) > 0.10 else "medium"

    return MatchPrediction(
        team_a_name=team_a_name,
        team_b_name=team_b_name,
        prob_a=round(prob_a, 3),
        prob_b=round(prob_b, 3),
        predicted_score_a=predicted_score_a,
        predicted_score_b=predicted_score_b,
        best_of=best_of,
        map_predictions=map_picks,
        confidence=overall_confidence,
        note="Placeholder prediction — real model coming in a future iteration",
    )


def predict_fantasy(
    team_a_players: list[str],
    team_b_players: list[str],
    best_of: int = 3,
) -> MatchPrediction:
    """Stub prediction for a custom fantasy roster."""
    return predict_match(
        team_a_name="Custom Team A",
        team_b_name="Custom Team B",
        best_of=best_of,
    )


@dataclass
class LossAnalysis:
    summary: str
    key_factors: list[str]
    standout_players: list[str]
    underperformers: list[str]


def explain_loss(match_id: int, team_lost: str, team_won: str) -> LossAnalysis:
    """Stub loss analysis. The real version will hit OpenAI with SHAP-attributed features.

    Returns hardcoded but match-appropriate text — enough to lock in the
    UI shape before we wire up GPT-4 in a later iteration.
    """
    return LossAnalysis(
        summary=(
            f"{team_lost} dropped this match to {team_won} primarily due to a breakdown in "
            f"midround coordination and weaker individual performances in key duelist roles. "
            f"While {team_lost}'s structured early-round play kept them competitive on defence, "
            f"{team_won}'s aggressive site-take pace consistently put them on the back foot. "
            f"This is placeholder analysis — once the AI explanation layer is connected, this "
            f"text will be generated from real match features."
        ),
        key_factors=[
            "Opening duel win rate dropped to ~38% (vs typical 50%+)",
            "Significantly lower KAST across the entire roster",
            "Pistol round losses on 2 of 3 maps",
            f"{team_won}'s controller play denied utility on critical executes",
        ],
        standout_players=[
            f"Opposition star player carried hard with 1.4+ rating across all maps",
            f"Counter-strat IGL adjustments mid-series proved decisive",
        ],
        underperformers=[
            f"{team_lost}'s primary duelist underperformed (~0.85 rating vs 1.20 career avg)",
            "Defensive role players showed lower-than-usual impact",
        ],
    )
