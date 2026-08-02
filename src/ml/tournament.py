"""Tournament forecasting — 'who wins this event?'

Given a set of participating teams, builds the pairwise win-probability matrix
with the trained model (reusing the exact same feature pipeline as the
head-to-head predictor), then Monte-Carlo-simulates a round-robin many times to
estimate each team's chance of finishing top of the standings.

Method (round-robin standings):
  - Everyone plays everyone once, each match a Bo-k decided by the model's
    pairwise probability.
  - Per simulation we tally wins, break ties for 1st randomly, and record the
    table-topper.
  - Aggregated over N sims this gives P(finish 1st), expected wins, and each
    team's average win probability vs the field.

This is intentionally format-agnostic: real events mix group stages and
playoffs, but a round-robin over the field is a transparent, seeding-free proxy
for overall event strength.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from ..app.predict import _build_features_for_teams
from .model import predict_match_proba

log = logging.getLogger(__name__)

# Deterministic RNG so the same field returns the same forecast (reproducible
# for the dissertation). Date/random-free by design.
_SEED = 42

# Small in-memory cache: (frozenset(team_ids), best_of) -> forecast dict.
_cache: dict[tuple, dict] = {}


def _pairwise_prob(a_id: int, b_id: int, best_of: int) -> Optional[float]:
    """P(team a beats team b) over a Bo-k, via the trained model. None if the
    features (i.e. a recent lineup) can't be built for one of the teams."""
    feats = _build_features_for_teams(a_id, b_id)
    if feats is None:
        return None
    res = predict_match_proba(feats, best_of=best_of)
    if res is None:
        return None
    return float(res["prob_a"])


def forecast_round_robin(
    teams: list[tuple[int, str]],
    best_of: int = 3,
    n_sims: int = 20000,
) -> dict:
    """Forecast an event from its participating teams.

    `teams` is a list of (team_id, name). Returns a dict with a per-team
    ranking by championship probability, plus any teams that had to be dropped
    for lack of data.
    """
    names = {tid: name for tid, name in teams}
    ids = list(names.keys())

    cache_key = (frozenset(ids), best_of, n_sims)
    if cache_key in _cache:
        return _cache[cache_key]

    # --- Pairwise probability matrix -------------------------------------
    pair_p: dict[tuple[int, int], float] = {}
    valid: set[int] = set()
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            p = _pairwise_prob(a, b, best_of)
            if p is None:
                continue
            pair_p[(a, b)] = p
            pair_p[(b, a)] = 1.0 - p
            valid.add(a)
            valid.add(b)

    participants = [tid for tid in ids if tid in valid]
    unavailable = [names[tid] for tid in ids if tid not in valid]
    m = len(participants)

    if m < 2:
        result = {
            "format": "round_robin",
            "best_of": best_of,
            "n_sims": 0,
            "n_teams": m,
            "teams": [],
            "unavailable": unavailable,
            "note": (
                "Not enough teams with recent lineup data to forecast. "
                "The model needs at least two teams that have played recently."
            ),
        }
        _cache[cache_key] = result
        return result

    # --- Monte Carlo round-robin -----------------------------------------
    rng = random.Random(_SEED)
    pairs = [
        (participants[i], participants[j])
        for i in range(m)
        for j in range(i + 1, m)
    ]
    champions = {tid: 0 for tid in participants}
    total_wins = {tid: 0 for tid in participants}

    for _ in range(n_sims):
        wins = {tid: 0 for tid in participants}
        for a, b in pairs:
            if rng.random() < pair_p.get((a, b), 0.5):
                wins[a] += 1
            else:
                wins[b] += 1
        for tid in participants:
            total_wins[tid] += wins[tid]
        top_score = max(wins.values())
        leaders = [tid for tid, w in wins.items() if w == top_score]
        champions[rng.choice(leaders)] += 1

    games = m - 1
    items = []
    for tid in participants:
        opp_probs = [pair_p[(tid, o)] for o in participants if o != tid]
        exp_wins = total_wins[tid] / n_sims
        items.append({
            "team_id": tid,
            "team_name": names[tid],
            "champion_prob": champions[tid] / n_sims,
            "expected_wins": round(exp_wins, 2),
            "win_rate": round(exp_wins / games, 4) if games else 0.0,
            "avg_win_prob": round(sum(opp_probs) / len(opp_probs), 4) if opp_probs else 0.0,
        })
    items.sort(key=lambda x: x["champion_prob"], reverse=True)

    result = {
        "format": "round_robin",
        "best_of": best_of,
        "n_sims": n_sims,
        "n_teams": m,
        "teams": items,
        "unavailable": unavailable,
        "note": (
            "Round-robin Monte Carlo over the field using the model's pairwise "
            f"Bo{best_of} probabilities. Championship % is P(finishing 1st)."
        ),
    }
    _cache[cache_key] = result
    return result
