"""Pipeline that ties together fetching, parsing, and persisting."""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from bs4 import BeautifulSoup
from sqlalchemy import select
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

# Words that are status badges rather than real event names. Used to decide
# whether to overwrite an existing Event.name in the DB.
_BAD_EVENT_NAMES = {"upcoming", "completed", "live", "final", "tbd", ""}


# --- Fetchers --------------------------------------------------------------


def fetch_results_page(page: int = 1) -> list[MatchListing]:
    if page == 1:
        url = f"{settings.vlr_base_url}/matches/results"
    else:
        url = f"{settings.vlr_base_url}/matches/results/?page={page}"
    html = fetch(url)
    return parse_results_listing(html, base_url=settings.vlr_base_url)


def fetch_event_matches(event_id: int) -> list[MatchListing]:
    url = f"{settings.vlr_base_url}/event/matches/{event_id}/?series_id=all"
    html = fetch(url)
    return parse_results_listing(html, base_url=settings.vlr_base_url)


def fetch_and_parse_match(url: str) -> MatchDetail:
    html = fetch(url)
    return parse_match_detail(html, match_url=url)


def discover_events(search: Optional[str] = None, limit: int = 25) -> list[tuple[int, str]]:
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
        name = " ".join(a.get_text().split())
        if not name or len(name) < 3 or name.lower() in _BAD_EVENT_NAMES:
            continue
        seen[eid] = name

    pairs = list(seen.items())
    if search:
        needle = search.lower()
        pairs = [(eid, name) for eid, name in pairs if needle in name.lower()]
    return pairs[:limit]


# --- Persistence -----------------------------------------------------------


def _team_id_for_player(detail: MatchDetail, ps: PlayerStat) -> int | None:
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


def _upsert_event(session: Session, event_id: int, parsed_name: Optional[str]) -> None:
    """Insert event if missing, update its name if the parsed one is better."""
    if event_id is None:
        return
    parsed_clean = (parsed_name or "").strip()
    if not parsed_clean or parsed_clean.lower() in _BAD_EVENT_NAMES:
        return  # nothing useful to write

    event = session.get(Event, event_id)
    if event is None:
        session.add(Event(id=event_id, name=parsed_clean))
        return

    current = (event.name or "").strip().lower()
    if current in _BAD_EVENT_NAMES or event.name != parsed_clean:
        # Either current is junk or differs from the new parse — overwrite
        event.name = parsed_clean


def upsert_match(session: Session, detail: MatchDetail) -> Match:
    # Teams
    for tid, tname in (
        (detail.team_a_id, detail.team_a_name),
        (detail.team_b_id, detail.team_b_name),
    ):
        if tid is not None and not session.get(Team, tid):
            session.add(Team(id=tid, name=tname or ""))

    # Event (insert or update name)
    _upsert_event(session, detail.event_id, detail.event_name)

    # Match
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

    session.query(PlayerMapStat).filter(PlayerMapStat.match_id == detail.match_id).delete()
    session.query(MapPlayed).filter(MapPlayed.match_id == detail.match_id).delete()
    session.query(VetoAction).filter(VetoAction.match_id == detail.match_id).delete()
    session.flush()

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


def _filter_existing(listings: list[MatchListing]) -> tuple[list[MatchListing], int]:
    """Drop listings whose match_id is already in the DB. Returns (kept, skipped)."""
    if not listings:
        return listings, 0
    ids = [l.match_id for l in listings]
    session = get_session()
    try:
        existing = set(
            row[0]
            for row in session.execute(select(Match.id).where(Match.id.in_(ids))).all()
        )
    finally:
        session.close()
    kept = [l for l in listings if l.match_id not in existing]
    return kept, len(listings) - len(kept)


def _scrape_listings(
    listings: list[MatchListing], label: str, force: bool = False
) -> dict[str, int]:
    stats = {"listed": len(listings), "skipped": 0, "ok": 0, "failed": 0, "player_rows": 0}

    if not force:
        listings, n_skipped = _filter_existing(listings)
        stats["skipped"] = n_skipped
        if n_skipped:
            log.info("Skipping %d match(es) already in DB (use --force to re-scrape)", n_skipped)

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
                    "Saved %d: %s %s-%s %s  event=%r  maps=%d  player_rows=%d",
                    detail.match_id,
                    detail.team_a_name,
                    detail.score_a if detail.score_a is not None else "?",
                    detail.score_b if detail.score_b is not None else "?",
                    detail.team_b_name,
                    detail.event_name or "?",
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


def scrape_recent(pages: int = 1, force: bool = False) -> dict[str, int]:
    listings: list[MatchListing] = []
    for p in range(1, pages + 1):
        try:
            page_listings = fetch_results_page(p)
        except HttpError as exc:
            log.error("Failed to fetch results page %d: %s", p, exc)
            continue
        listings.extend(page_listings)
    seen_ids: set[int] = set()
    unique: list[MatchListing] = []
    for l in listings:
        if l.match_id in seen_ids:
            continue
        seen_ids.add(l.match_id)
        unique.append(l)
    return _scrape_listings(unique, f"recent ({pages} page(s))", force=force)


def scrape_event(event_id: int, force: bool = False) -> dict[str, int]:
    try:
        listings = fetch_event_matches(event_id)
    except HttpError as exc:
        log.error("Failed to fetch event %d matches: %s", event_id, exc)
        return {"listed": 0, "skipped": 0, "ok": 0, "failed": 0, "player_rows": 0}
    return _scrape_listings(listings, f"event {event_id}", force=force)


def scrape_match_ids(match_ids: Iterable[int], force: bool = True) -> dict[str, int]:
    """Explicit match IDs default to force=True since the user named them."""
    listings = [
        MatchListing(match_id=mid, url=f"{settings.vlr_base_url}/{mid}/_")
        for mid in match_ids
    ]
    return _scrape_listings(listings, f"{len(listings)} explicit match id(s)", force=force)


# --- Maintenance ----------------------------------------------------------


def repair_event_names() -> dict[str, int]:
    """Fix events whose name is a status word by re-parsing one match per event.

    Much faster than scrape-event because it only fetches the bare minimum.
    """
    stats = {"checked": 0, "fixed": 0, "no_match": 0, "failed": 0}
    session = get_session()
    try:
        bad_events = (
            session.execute(
                select(Event).where(
                    Event.name.in_(["upcoming", "completed", "live", "final", "tbd", ""])
                )
            )
            .scalars()
            .all()
        )
        stats["checked"] = len(bad_events)
        if not bad_events:
            return stats

        log.info("Found %d event(s) with bad names, repairing...", len(bad_events))

        for event in bad_events:
            match = session.execute(
                select(Match).where(Match.event_id == event.id).limit(1)
            ).scalar_one_or_none()

            if match is None:
                log.warning("Event %d has no matches in DB — cannot repair", event.id)
                stats["no_match"] += 1
                continue

            try:
                detail = fetch_and_parse_match(match.url)
            except Exception:
                log.exception("Failed to re-fetch match %d for event %d", match.id, event.id)
                stats["failed"] += 1
                continue

            if (
                detail.event_name
                and detail.event_name.strip().lower() not in _BAD_EVENT_NAMES
            ):
                old = event.name
                event.name = detail.event_name.strip()
                session.commit()
                log.info("  event %d: '%s' → '%s'", event.id, old, event.name)
                stats["fixed"] += 1
            else:
                log.warning("  event %d: re-parse still yielded no useful name", event.id)
                stats["failed"] += 1
    finally:
        session.close()
    return stats
