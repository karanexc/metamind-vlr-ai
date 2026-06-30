"""Background scheduler — re-scrapes vlr.gg every N minutes to keep the
'live results' on the home page actually live.

Implementation note: uses apscheduler's AsyncIOScheduler. The scrape runs
in a background thread so it doesn't block the API. If scraping fails
(network issue, vlr.gg rate-limiting us), the error is logged and the
next tick proceeds normally.

Disable by setting LIVE_SCRAPE_ENABLED=false in the environment.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger(__name__)


# Interval in minutes between scrapes. Configurable via env.
_INTERVAL_MIN = int(os.environ.get("LIVE_SCRAPE_INTERVAL_MIN", "30"))
_ENABLED = os.environ.get("LIVE_SCRAPE_ENABLED", "true").lower() == "true"

scheduler: AsyncIOScheduler | None = None


def _run_scrape() -> None:
    """Called by the scheduler on each tick."""
    if not _ENABLED:
        return
    log.info("[live-scrape] tick at %s", datetime.utcnow().isoformat())
    try:
        from ..scraping.pipeline import scrape_recent_results
        n = scrape_recent_results(pages=1)
        log.info("[live-scrape] %d new matches inserted", n)
    except Exception:
        log.exception("[live-scrape] failed")


def start_scheduler() -> None:
    """Idempotent — safe to call multiple times."""
    global scheduler
    if not _ENABLED:
        log.info("[live-scrape] disabled via LIVE_SCRAPE_ENABLED=false")
        return
    if scheduler is not None:
        return
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_scrape,
        "interval",
        minutes=_INTERVAL_MIN,
        next_run_time=datetime.utcnow(),  # run once immediately on startup
        id="live_scrape",
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    log.info("[live-scrape] scheduler started, interval=%d min", _INTERVAL_MIN)


def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        log.info("[live-scrape] scheduler stopped")
