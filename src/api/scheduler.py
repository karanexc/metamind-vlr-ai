"""Background scheduler — runs a full data-refresh cycle on an interval, and
lets the UI trigger the same refresh on demand.

The refresh (see pipeline.run_full_refresh) is fully incremental: new matches
skip ones already stored, profile/logo backfills skip already-populated rows,
and rankings/tiers just overwrite with fresh values. So re-running only does
work for new/changed data.

A refresh is guarded by a `_running` flag: if one is already in progress (from
the timer or a manual click), another trigger is skipped rather than run twice.

Config via environment:
  LIVE_SCRAPE_ENABLED       "true"/"false"  (default true)
  LIVE_SCRAPE_INTERVAL_MIN  minutes between refreshes (default 300 = 5h)
  LIVE_SCRAPE_PAGES         results pages scraped per refresh (default 1)
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger(__name__)

_INTERVAL_MIN = int(os.environ.get("LIVE_SCRAPE_INTERVAL_MIN", "300"))  # 5 hours
_PAGES = int(os.environ.get("LIVE_SCRAPE_PAGES", "1"))
_ENABLED = os.environ.get("LIVE_SCRAPE_ENABLED", "true").lower() == "true"

scheduler: Optional[AsyncIOScheduler] = None

# --- Run state -----------------------------------------------------------
_lock = threading.Lock()
_running = False
_last_run_at: Optional[datetime] = None
_last_result: Optional[dict] = None
_last_status = "never"  # never | running | ok | error


def _do_full_refresh() -> dict:
    """Run one full refresh. Guarded so it never runs twice concurrently."""
    global _running, _last_run_at, _last_result, _last_status
    with _lock:
        if _running:
            log.info("[refresh] already running — skipping this trigger")
            return {"status": "already_running"}
        _running = True
        _last_status = "running"

    log.info("[refresh] full refresh started at %s", datetime.utcnow().isoformat())
    try:
        from ..scraping.pipeline import run_full_refresh
        result = run_full_refresh(pages=_PAGES)
        with _lock:
            _last_run_at = datetime.utcnow()
            _last_result = result
            _last_status = "ok"
        log.info("[refresh] done: %s", result)
        return result
    except Exception:
        with _lock:
            _last_run_at = datetime.utcnow()
            _last_status = "error"
        log.exception("[refresh] failed")
        return {"status": "error"}
    finally:
        with _lock:
            _running = False


def _run_scheduled() -> None:
    """Timer entrypoint (respects the enabled flag)."""
    if not _ENABLED:
        return
    _do_full_refresh()


def run_now() -> dict:
    """Kick off a full refresh in the background and return immediately.

    If a refresh is already running (timer or a previous click), this is a
    no-op that reports so — the in-flight run will finish the work.
    """
    with _lock:
        if _running:
            return {"status": "already_running", "started": False}
    threading.Thread(target=_do_full_refresh, name="vlr-full-refresh", daemon=True).start()
    return {"status": "started", "started": True}


def get_status() -> dict:
    next_run: Optional[str] = None
    if scheduler is not None:
        job = scheduler.get_job("full_refresh")
        if job is not None and job.next_run_time is not None:
            next_run = job.next_run_time.isoformat()
    with _lock:
        return {
            "enabled": _ENABLED,
            "interval_minutes": _INTERVAL_MIN,
            "status": _last_status,
            "running": _running,
            "last_run": _last_run_at.isoformat() if _last_run_at else None,
            "last_result": _last_result,
            "next_run": next_run,
        }


def start_scheduler() -> None:
    """Idempotent — safe to call multiple times."""
    global scheduler
    if not _ENABLED:
        log.info("[refresh] disabled via LIVE_SCRAPE_ENABLED=false")
        return
    if scheduler is not None:
        return
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_scheduled,
        "interval",
        minutes=_INTERVAL_MIN,
        next_run_time=datetime.utcnow(),  # run once immediately on startup
        id="full_refresh",
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    log.info("[refresh] scheduler started, interval=%d min", _INTERVAL_MIN)


def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        log.info("[refresh] scheduler stopped")
