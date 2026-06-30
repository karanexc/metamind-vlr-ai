"""Prediction endpoints — match and fantasy."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from vlr.app import data, predict as predict_layer
from vlr.api.limits import limiter
from vlr.api.schemas import (
    FantasyRequest,
    MapPrediction,
    MatchPrediction,
    PredictRequest,
)

router = APIRouter()


def _prediction_to_schema(p) -> MatchPrediction:
    return MatchPrediction(
        team_a_name=p.team_a_name,
        team_b_name=p.team_b_name,
        prob_a=p.prob_a,
        prob_b=p.prob_b,
        predicted_score_a=p.predicted_score_a,
        predicted_score_b=p.predicted_score_b,
        best_of=p.best_of,
        map_predictions=[
            MapPrediction(
                map_name=m.map_name, prob_a=m.prob_a,
                prob_b=m.prob_b, confidence=m.confidence,
            )
            for m in p.map_predictions
        ],
        confidence=p.confidence,
        note=p.note,
        cross_tier_warning=getattr(p, "cross_tier_warning", None),
    )


def _team_name(team_id: int) -> str:
    """Look up a team name from its ID. Raises 404 if not found."""
    for tid, name, _ in data.get_team_options(min_matches=1):
        if tid == team_id:
            return name
    raise HTTPException(status_code=404, detail=f"Team {team_id} not found")


@router.post("/predict", response_model=MatchPrediction)
@limiter.limit("10/minute")
async def predict_match(request: Request, body: PredictRequest) -> MatchPrediction:
    """Predict the outcome of a hypothetical match between two real teams.

    Rate limited per IP — prevents anyone from running up the OpenAI bill.
    """
    if body.team_a_id == body.team_b_id:
        raise HTTPException(status_code=400, detail="team_a_id and team_b_id must differ")
    if body.best_of not in (1, 3, 5):
        raise HTTPException(status_code=400, detail="best_of must be 1, 3, or 5")

    team_a_name = _team_name(body.team_a_id)
    team_b_name = _team_name(body.team_b_id)

    result = predict_layer.predict_match(
        team_a_name=team_a_name,
        team_b_name=team_b_name,
        team_a_id=body.team_a_id,
        team_b_id=body.team_b_id,
        best_of=body.best_of,
    )
    return _prediction_to_schema(result)


@router.post("/predict/fantasy", response_model=MatchPrediction)
@limiter.limit("10/minute")
async def predict_fantasy(request: Request, body: FantasyRequest) -> MatchPrediction:
    """Predict outcome between two custom 5-player rosters."""
    if len(body.team_a_players) != 5 or len(body.team_b_players) != 5:
        raise HTTPException(status_code=400, detail="Each team needs exactly 5 players")
    if body.best_of not in (1, 3, 5):
        raise HTTPException(status_code=400, detail="best_of must be 1, 3, or 5")

    result = predict_layer.predict_fantasy(
        team_a_players=body.team_a_players,
        team_b_players=body.team_b_players,
        best_of=body.best_of,
    )
    return _prediction_to_schema(result)
