"""Pick'em — tournament winner forecasting from a set of participating teams."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from vlr.app import data
from vlr.api.limits import limiter
from vlr.api.schemas import EventTeam, PickemForecast, PickemRequest

router = APIRouter()


@router.get("/pickem/events/{event_id}/teams", response_model=list[EventTeam])
async def event_teams(event_id: int) -> list[EventTeam]:
    """Teams participating in an event (auto-populates the Pick'em picker)."""
    rows = data.get_event_teams(event_id)
    return [EventTeam(id=tid, name=name) for tid, name in rows]


@router.post("/pickem/forecast", response_model=PickemForecast)
@limiter.limit("6/minute")
async def pickem_forecast(request: Request, body: PickemRequest) -> PickemForecast:
    """Forecast which team is most likely to win an event, via round-robin
    Monte Carlo over the model's pairwise probabilities."""
    if body.best_of not in (1, 3, 5):
        raise HTTPException(status_code=400, detail="best_of must be 1, 3, or 5")
    if len(body.team_ids) < 2:
        raise HTTPException(status_code=400, detail="Pick at least two teams")
    if len(body.team_ids) > 24:
        raise HTTPException(status_code=400, detail="At most 24 teams supported")

    n_sims = max(1000, min(body.n_sims, 50000))

    # Resolve display names for the requested team ids.
    name_map = {tid: name for tid, name, _ in data.get_team_options(min_matches=1)}
    teams = [(tid, name_map.get(tid, f"Team {tid}")) for tid in dict.fromkeys(body.team_ids)]

    from vlr.ml.tournament import forecast_round_robin

    result = await run_in_threadpool(forecast_round_robin, teams, body.best_of, n_sims)
    return PickemForecast(**result)
