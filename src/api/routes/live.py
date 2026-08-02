"""Live-scrape status + manual refresh endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

from vlr.api.limits import limiter
from vlr.api.scheduler import get_status, run_now
from vlr.api.schemas import LiveStatus, RefreshResult

router = APIRouter()


@router.get("/live/status", response_model=LiveStatus)
async def live_status() -> LiveStatus:
    """Current state of the refresh cycle (running?, last run, next run, interval)."""
    return LiveStatus(**get_status())


@router.post("/live/refresh", response_model=RefreshResult)
@limiter.limit("4/minute")
async def live_refresh(request: Request) -> RefreshResult:
    """Kick off a full data refresh in the background ('Refresh now' button).

    Returns immediately; if a refresh is already running the request is a no-op.
    Rate limited to protect vlr.gg from hammering.
    """
    return RefreshResult(**run_now())
