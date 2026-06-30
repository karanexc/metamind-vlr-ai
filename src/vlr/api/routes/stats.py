"""GET /stats — dataset overview."""
from __future__ import annotations

from fastapi import APIRouter

from vlr.app import data
from vlr.api.schemas import DatabaseStats

router = APIRouter()


@router.get("/stats", response_model=DatabaseStats)
async def get_stats() -> DatabaseStats:
    s = data.get_database_stats()
    return DatabaseStats(
        matches=s.matches,
        real_matches=s.real_matches,
        teams=s.teams,
        events=s.events,
        players=s.players,
        maps=s.maps,
        player_rows=s.player_rows,
        earliest_match=s.earliest_match,
        latest_match=s.latest_match,
    )
