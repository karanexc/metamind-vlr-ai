"""Live-scrape status + manual refresh endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from vlr.api.limits import limiter
from vlr.api.scheduler import get_status, run_now
from vlr.api.schemas import LiveStatus, RefreshResult

router = APIRouter()


@router.get("/live/status", response_model=LiveStatus)
async def live_status() -> LiveStatus:
    """Current state of the background scraper (last run, next run, interval)."""
    return LiveStatus(**get_status())


@router.post("/live/refresh", response_model=RefreshResult)
@limiter.limit("4/minute")
async def live_refresh(request: Request) -> RefreshResult:
    """Trigger an immediate scrape of recent results ('Refresh now' button).

    Runs in a threadpool so the network-bound scrape doesn't block the event
    loop. Rate limited to protect vlr.gg from hammering.
    """
    res = await run_in_threadpool(run_now)
    return RefreshResult(**res)
