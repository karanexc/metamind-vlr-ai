"""Player depth analysis — a player's performance timeline within one event."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from vlr.app import data
from vlr.api.schemas import EventPlayer, PlayerEventAnalysis

router = APIRouter()


@router.get("/depth/events/{event_id}/players", response_model=list[EventPlayer])
async def event_players(event_id: int) -> list[EventPlayer]:
    """Players who appeared in an event (to populate the player picker)."""
    rows = data.get_event_players(event_id)
    return [EventPlayer(id=pid, name=name, n_maps=n) for pid, name, n in rows]


@router.get(
    "/depth/events/{event_id}/players/{player_id}",
    response_model=PlayerEventAnalysis,
)
async def player_event_analysis(event_id: int, player_id: int) -> PlayerEventAnalysis:
    """A player's per-map timeline + aggregates for one event."""
    res = data.get_player_event_analysis(player_id, event_id)
    if res is None:
        raise HTTPException(status_code=404, detail="No data for that player in that event")
    return PlayerEventAnalysis(**res)
