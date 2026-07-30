"""Background scheduler — re-scrapes vlr.gg on an interval to keep the
'live results' actually live, plus an on-demand refresh used by the UI's
"Refresh now" button.

Implementation note: uses apscheduler's AsyncIOScheduler. The scrape runs
in a background thread so it doesn't block the API. If scraping fails
(network issue, vlr.gg rate-limiting us), the error is logged and the
next tick proceeds normally.

Config via environment:
  LIVE_SCRAPE_ENABLED       "true"/"false"  (default true)
  LIVE_SCRAPE_INTERVAL_MIN  minutes between scrapes (default 120 = 2h)
  LIVE_SCRAPE_PAGES         results pages to scrape per tick (default 1)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from threading import Lock
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger(__name__)


# Interval in minutes between scrapes. Default 2h; configurable via env.
_INTERVAL_MIN = int(os.environ.get("LIVE_SCRAPE_INTERVAL_MIN", "120"))
_PAGES = int(os.environ.get("LIVE_SCRAPE_PAGES", "1"))
_ENABLED = os.environ.get("LIVE_SCRAPE_ENABLED", "true").lower() == "true"

scheduler: Optional[AsyncIOScheduler] = None

# --- Run state (exposed via /live/status) --------------------------------
_lock = Lock()
_last_run_at: Optional[datetime] = None
_last_inserted: Optional[int] = None
_last_status: str = "never"  # "never" | "running" | "ok" | "error"


def _do_scrape() -> int:
    """Run one scrape pass. Returns count of newly-inserted matches.

    Updates the module-level run state so /live/status can report it.
    Never raises — errors are captured into the status.
    """
    global _last_run_at, _last_inserted, _last_status
    with _lock:
        _last_status = "running"
    log.info("[live-scrape] tick at %s", datetime.utcnow().isoformat())
    try:
        from ..scraping.pipeline import scrape_recent_results
        n = scrape_recent_results(pages=_PAGES)
        with _lock:
            _last_run_at = datetime.utcnow()
            _last_inserted = n
            _last_status = "ok"
        log.info("[live-scrape] %d new match(es) inserted", n)
        return n
    except Exception:
        with _lock:
            _last_run_at = datetime.utcnow()
            _last_status = "error"
        log.exception("[live-scrape] failed")
        return 0


def _run_scrape() -> None:
    """Scheduled-tick entrypoint (respects the enabled flag)."""
    if not _ENABLED:
        return
    _do_scrape()


def run_now() -> dict:
    """Trigger an immediate scrape (used by the manual refresh endpoint).

    Runs synchronously in the calling thread and returns a small result dict.
    Safe to call regardless of whether the scheduler is enabled.
    """
    n = _do_scrape()
    return {"inserted": n, "ran_at": _last_run_at.isoformat() if _last_run_at else None}


def get_status() -> dict:
    """Snapshot of the live-scrape state for the /live/status endpoint."""
    next_run: Optional[str] = None
    if scheduler is not None:
        job = scheduler.get_job("live_scrape")
        if job is not None and job.next_run_time is not None:
            next_run = job.next_run_time.isoformat()
    with _lock:
        return {
            "enabled": _ENABLED,
            "interval_minutes": _INTERVAL_MIN,
            "status": _last_status,
            "last_run": _last_run_at.isoformat() if _last_run_at else None,
            "last_inserted": _last_inserted,
            "next_run": next_run,
        }


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
