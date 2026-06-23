"""Rate-limited HTTP client for vlr.gg.

Single global delay between requests, exponential backoff on transient errors,
and a User-Agent that identifies the dissertation project to site admins.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

log = logging.getLogger(__name__)


class _Throttle:
    """Process-wide minimum interval between requests."""

    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed_at - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._next_allowed_at = time.monotonic() + self.min_interval


_throttle = _Throttle(settings.scrape_delay_seconds)


class HttpError(Exception):
    pass


class TransientHttpError(HttpError):
    pass


class PermanentHttpError(HttpError):
    pass


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(TransientHttpError),
)
def fetch(url: str, params: Optional[dict] = None) -> str:
    """Fetch a URL with throttling and retries. Returns the response body as text."""
    _throttle.wait()
    headers = {
        "User-Agent": settings.scrape_user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    log.debug("GET %s", url)
    try:
        resp = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.scrape_timeout_seconds,
        )
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise TransientHttpError(f"Network error fetching {url}: {exc}") from exc

    if resp.status_code in (429, 500, 502, 503, 504):
        raise TransientHttpError(f"{resp.status_code} for {url}")
    if resp.status_code >= 400:
        raise PermanentHttpError(f"{resp.status_code} for {url}")
    return resp.text
