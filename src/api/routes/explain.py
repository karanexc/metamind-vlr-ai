"""LLM match analysis endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from vlr.app import data, predict as predict_layer
from vlr.api.limits import limiter
from vlr.api.schemas import LossAnalysis

router = APIRouter()


@router.get("/explain/{match_id}", response_model=LossAnalysis)
@limiter.limit("5/minute")
async def explain_match(
    request: Request,
    match_id: int,
    regenerate: bool = Query(False, description="Force a fresh OpenAI call"),
) -> LossAnalysis:
    """Get LLM-generated analysis for a completed match.

    Cached in the DB after first call — subsequent calls for the same match
    return instantly. Use `regenerate=true` to force a fresh API call.

    Rate-limited heavily because each call costs ~$0.005 in OpenAI fees.
    """
    detail = data.get_match_detail(match_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    if detail["score_a"] is None or detail["score_b"] is None:
        raise HTTPException(
            status_code=400,
            detail=f"Match {match_id} has no scores yet (forfeit or upcoming)",
        )

    a_won = detail["score_a"] > detail["score_b"]
    winner_name = detail["team_a_name"] if a_won else detail["team_b_name"]
    loser_name = detail["team_b_name"] if a_won else detail["team_a_name"]

    if regenerate:
        result = predict_layer.explain_loss_regenerate(
            match_id=match_id, team_lost=loser_name, team_won=winner_name,
        )
    else:
        result = predict_layer.explain_loss(
            match_id=match_id, team_lost=loser_name, team_won=winner_name,
        )

    return LossAnalysis(
        summary=result.summary,
        key_factors=result.key_factors,
        standout_players=result.standout_players,
        underperformers=result.underperformers,
    )
