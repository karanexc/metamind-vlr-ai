"""Agent meta — pick/win rates per agent, optionally scoped to a map."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from vlr.app import data
from vlr.api.schemas import AgentMetaItem

router = APIRouter()


@router.get("/meta/maps", response_model=list[str])
async def meta_maps() -> list[str]:
    """Distinct map names, for the meta page's map filter."""
    return data.get_map_names()


@router.get("/meta/agents", response_model=list[AgentMetaItem])
async def meta_agents(
    map_name: Optional[str] = Query(None, alias="map"),
    min_picks: int = Query(20, ge=1),
) -> list[AgentMetaItem]:
    """Per-agent meta stats, optionally scoped to a single map."""
    rows = data.get_agent_meta(map_name=map_name, min_picks=min_picks)
    return [AgentMetaItem(**r) for r in rows]
