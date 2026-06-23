"""Pipeline that ties together fetching, parsing, and persisting."""
from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import (
    Event,
    MapPlayed,
    Match,
    Player,
    PlayerMapStat,
    Team,
    VetoAction,
)
from ..db.session import get_session
from .client import HttpError, fetch
from .parsers import (
    EVENT_URL_RE,
    MatchDetail,
    MatchListing,
    PlayerStat,
    parse_match_detail,
    parse_results_listing,
)

log = logging.getLogger(__name__)


# --- Fetchers --------------------------------------------------------------


def fetch_results_page(page: int = 1) -> list[MatchListing]:
    if page == 1:
        url = f"{settings.vlr_base_url}/matches/results"
    else:
        url = f"{settings.vlr_base_url}/matches/results/?page={page}"
    html = fetch(url)
    return parse_results_listing(html, base_url=settings.vlr_base_url)


def fetch_event_matches(event_id: int) -> list[MatchListing]:
    """Fetch all match links from an event's matches page."""
    url = f"{settings.vlr_base_url}/event/matches/{event_id}/?series_id=all"
    html = fetch(url)
    return parse_results_listing(html, base_url=settings.vlr_base_url)


def fetch_and_parse_match(url: str) -> MatchDetail:
    html = fetch(url)
    return parse_match_detail(html, match_url=url)


def discover_events(search: Optional[str] = None, limit: int = 25) -> list[tuple[int, str]]:
    """Scrape vlr.gg's /events page and return (event_id, name) pairs.

    Optionally filter by case-insensitive substring match against the name.
    Does NOT persist anything — purely a lookup helper for finding event IDs.
    """
    url = f"{settings.vlr_base_url}/events"
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")

    seen: dict[int, str] = {}
    for a in soup.find_all("a", href=EVENT_URL_RE):
        m = EVENT_URL_RE.match(a["href"])
        if not m:
            continue
        eid = int(m.group(1))
        if eid in seen:
            continue
        # Prefer the longer, more descriptive name (skip empty anchors that
        # just wrap an icon, etc.)
        name = " ".join(a.get_text().split())
        if not name or len(name) < 3:
            continue
        seen[eid] = name

    pairs = list(seen.items())
    if search:
        needle = search.lower()
        pairs = [(eid, name) for eid, name in pairs if needle in name.lower()]
    return pairs[:limit]


# --- Persistence -----------------------------------------------------------


def _team_id_for_player(detail: MatchDetail, ps: PlayerStat) -> int | None:
    """Resolve a player's team_id via tbody position (most reliable), with
    a fallback to matching the parsed short team tag against full names."""
    if ps.team_index == 0:
        return detail.team_a_id
    if ps.team_index == 1:
        return detail.team_b_id

    if ps.team_name:
        tag = ps.team_name.strip().lower()
        a_name = (detail.team_a_name or "").lower()
        b_name = (detail.team_b_name or "").lower()
        if tag and (tag in a_name or a_name.startswith(tag)):
            return detail.team_a_id
        if tag and (tag in b_name or b_name.startswith(tag)):
            return detail.team_b_id
    return None


def upsert_match(session: Session, detail: MatchDetail) -> Match:
    """Persist a parsed match. Idempotent — wholesale replaces child rows."""
    # Teams
    for tid, tname in (
        (detail.team_a_id, detail.team_a_name),
        (detail.team_b_id, detail.team_b_name),
    ):
        if tid is not None and not session.get(Team, tid):
            session.add(Team(id=tid, name=tname or ""))

    # Event
    if detail.event_id is not None and detail.event_name:
        if not session.get(Event, detail.event_id):
            session.add(Event(id=detail.event_id, name=detail.event_name))

    # Match (insert or update)
    match = session.get(Match, detail.match_id)
    if match is None:
        match = Match(id=detail.match_id, url=detail.url, team_a_name="", team_b_name="")
        session.add(match)

    match.url = detail.url
    match.event_id = detail.event_id
    match.team_a_id = detail.team_a_id
    match.team_b_id = detail.team_b_id
    match.team_a_name = detail.team_a_name
    match.team_b_name = detail.team_b_name
    match.score_a = detail.score_a
    match.score_b = detail.score_b
    match.best_of = detail.best_of
    match.stage = detail.stage
    match.patch = detail.patch
    match.match_datetime = detail.match_datetime
    match.veto_raw = detail.veto_raw

    # Wipe child rows
    session.query(PlayerMapStat).filter(PlayerMapStat.match_id == detail.match_id).delete()
    session.query(MapPlayed).filter(MapPlayed.match_id == detail.match_id).delete()
    session.query(VetoAction).filter(VetoAction.match_id == detail.match_id).delete()
    session.flush()

    # Re-insert maps and player stats
    for m in detail.maps:
        db_map = MapPlayed(
            match_id=detail.match_id,
            map_index=m.map_index,
            map_name=m.map_name,
            score_a=m.score_a,
            score_b=m.score_b,
            picked_by=m.picked_by,
        )
        session.add(db_map)
        session.flush()

        for ps in m.player_stats:
            if not session.get(Player, ps.player_id):
                session.add(Player(id=ps.player_id, name=ps.player_name))
                session.flush()

            session.add(
                PlayerMapStat(
                    match_id=detail.match_id,
                    map_id=db_map.id,
                    player_id=ps.player_id,
                    team_id=_team_id_for_player(detail, ps),
                    team_name=ps.team_name,
                    agent=ps.agent,
                    rating=ps.rating,
                    acs=ps.acs,
                    kills=ps.kills,
                    deaths=ps.deaths,
                    assists=ps.assists,
                    plus_minus=ps.plus_minus,
                    kast=ps.kast,
                    adr=ps.adr,
                    hs_pct=ps.hs_pct,
                    fk=ps.fk,
                    fd=ps.fd,
                    fk_fd_diff=ps.fk_fd_diff,
                )
            )

    for v in detail.veto_actions:
        session.add(
            VetoAction(
                match_id=detail.match_id,
                order_index=v.order_index,
                team_name=v.team_name,
                action=v.action,
                map_name=v.map_name,
            )
        )

    return match


# --- High-level scraping -------------------------------------------------


def _scrape_listings(listings: list[MatchListing], label: str) -> dict[str, int]:
    """Shared driver: iterate a list of match links, fetch + parse + persist."""
    stats = {"listed": len(listings), "ok": 0, "failed": 0, "player_rows": 0}
    log.info("Scraping %d matches for %s", len(listings), label)

    session = get_session()
    try:
        for listing in listings:
            try:
                detail = fetch_and_parse_match(listing.url)
            except HttpError as exc:
                log.warning("Skipping %s (%s)", listing.url, exc)
                stats["failed"] += 1
                continue
            except Exception:
                log.exception("Parse error for %s", listing.url)
                stats["failed"] += 1
                continue

            try:
                upsert_match(session, detail)
                session.commit()
                stats["ok"] += 1
                n_rows = sum(len(m.player_stats) for m in detail.maps)
                stats["player_rows"] += n_rows
                log.info(
                    "Saved %d: %s %s-%s %s  maps=%d  player_rows=%d",
                    detail.match_id,
                    detail.team_a_name,
                    detail.score_a if detail.score_a is not None else "?",
                    detail.score_b if detail.score_b is not None else "?",
                    detail.team_b_name,
                    len(detail.maps),
                    n_rows,
                )
            except Exception:
                session.rollback()
                log.exception("DB error persisting match %d", detail.match_id)
                stats["failed"] += 1
    finally:
        session.close()

    return stats


def scrape_recent(pages: int = 1) -> dict[str, int]:
    listings: list[MatchListing] = []
    for p in range(1, pages + 1):
        try:
            page_listings = fetch_results_page(p)
        except HttpError as exc:
            log.error("Failed to fetch results page %d: %s", p, exc)
            continue
        listings.extend(page_listings)
    # De-duplicate by match_id (in case of overlap across pages)
    seen_ids: set[int] = set()
    unique: list[MatchListing] = []
    for l in listings:
        if l.match_id in seen_ids:
            continue
        seen_ids.add(l.match_id)
        unique.append(l)
    return _scrape_listings(unique, f"recent ({pages} page(s))")


def scrape_event(event_id: int) -> dict[str, int]:
    """Scrape every completed match in a specific event."""
    try:
        listings = fetch_event_matches(event_id)
    except HttpError as exc:
        log.error("Failed to fetch event %d matches: %s", event_id, exc)
        return {"listed": 0, "ok": 0, "failed": 0, "player_rows": 0}
    return _scrape_listings(listings, f"event {event_id}")


def scrape_match_ids(match_ids: Iterable[int]) -> dict[str, int]:
    listings = [
        MatchListing(match_id=mid, url=f"{settings.vlr_base_url}/{mid}/_")
        for mid in match_ids
    ]
    return _scrape_listings(listings, f"{len(listings)} explicit match id(s)")
