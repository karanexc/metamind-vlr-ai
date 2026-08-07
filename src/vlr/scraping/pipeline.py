"""Pipeline that ties together fetching, parsing, and persisting."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..regions import VLR_REGION_SLUGS
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
    EventListing,
    MatchDetail,
    MatchListing,
    PlayerStat,
    RankedTeam,
    parse_events_listing,
    parse_match_detail,
    parse_rankings,
    parse_results_listing,
)

log = logging.getLogger(__name__)

_BAD_EVENT_NAMES = {"upcoming", "completed", "live", "final", "tbd", "ongoing", ""}

# vlr.gg's actual tier IDs (from /events page filter links)
VLR_TIER_IDS = {
    "vct": "60",            # VCT International + Regional Leagues
    "vcl": "61",            # Challengers
    "challengers": "61",
    "t3": "62",
    "gc": "63",
    "game-changers": "63",
    "collegiate": "64",
    "offseason": "67",
}

# vlr.gg's region IDs
VLR_REGION_IDS = {
    "americas": "26", "amer": "26", "na": "26",
    "emea": "27", "eu": "27",
    "pacific": "28", "pac": "28", "ap": "28",
    "cn": "24", "china": "24",
}

# Category → which vlr tier(s) to fetch, plus a client-side filter
CATEGORY_VLR_TIERS = {
    "international": "vct",
    "regional": "vct",
    "challengers": "vcl",
    "gc": "gc",
    "all-vct": "vct",
}


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


def fetch_upcoming_page(page: int = 1) -> list[MatchListing]:
    """vlr's upcoming/scheduled matches (the /matches feed, not /matches/results)."""
    if page == 1:
        url = f"{settings.vlr_base_url}/matches"
    else:
        url = f"{settings.vlr_base_url}/matches/?page={page}"
    html = fetch(url)
    return parse_results_listing(html, base_url=settings.vlr_base_url)


def scrape_upcoming(pages: int = 1) -> int:
    """Ingest upcoming matches (teams + scheduled time, null scores) so the
    predictor can call them before they're played. Skips existing; best-effort."""
    listings: list[MatchListing] = []
    for p in range(1, pages + 1):
        try:
            listings.extend(fetch_upcoming_page(p))
        except HttpError as exc:
            log.error("Failed to fetch upcoming page %d: %s", p, exc)
    if not listings:
        return 0
    try:
        return _scrape_listings(listings, f"{len(listings)} upcoming match(es)").get("ok", 0)
    except Exception:
        log.exception("scrape_upcoming failed")
        return 0


def fetch_and_parse_match(url: str) -> MatchDetail:
    html = fetch(url)
    return parse_match_detail(html, match_url=url)


def fetch_events_page(
    page: int = 1,
    vlr_tier: Optional[str] = None,
    region: Optional[str] = None,
) -> list[EventListing]:
    """Fetch one page of the events listing using vlr.gg's URL filters.

    vlr_tier: one of 'vct', 'vcl', 'gc', 't3' (uses vlr.gg's tier IDs).
    region: 'americas', 'emea', 'pacific', 'cn' (uses vlr.gg's region IDs).
    """
    params: list[str] = []
    if page > 1:
        params.append(f"page={page}")
    if vlr_tier:
        tid = VLR_TIER_IDS.get(vlr_tier.lower())
        if tid:
            params.append(f"tier={tid}")
        else:
            log.warning("Unknown vlr_tier %r — ignoring", vlr_tier)
    if region:
        rid = VLR_REGION_IDS.get(region.lower())
        if rid:
            params.append(f"region={rid}")
        else:
            log.warning("Unknown region %r — ignoring", region)

    base = f"{settings.vlr_base_url}/events"
    if params:
        url = f"{base}/?{'&'.join(params)}"
    else:
        url = base

    log.debug("Fetching events page: %s", url)
    html = fetch(url)
    return parse_events_listing(html, base_url=settings.vlr_base_url)


# --- Event discovery -------------------------------------------------------


def discover_events(
    search: Optional[str] = None,
    category: Optional[str] = None,
    year: Optional[int] = None,
    since_year: Optional[int] = None,
    region: Optional[str] = None,
    status: Optional[str] = None,
    max_pages: int = 8,
    limit: Optional[int] = None,
) -> list[EventListing]:
    """Paginate through /events and return EventListings matching filters.

    category: one of 'international', 'regional', 'challengers', 'gc', 'all-vct',
              or None (no category filter — fetches all events).
    """
    results: list[EventListing] = []
    seen_ids: set[int] = set()
    needle = search.lower() if search else None
    cat_norm = category.lower() if category else None
    vlr_tier = CATEGORY_VLR_TIERS.get(cat_norm) if cat_norm else None

    for page in range(1, max_pages + 1):
        try:
            listings = fetch_events_page(page=page, vlr_tier=vlr_tier, region=region)
        except HttpError as exc:
            log.warning("Failed to fetch events page %d: %s", page, exc)
            break

        if not listings:
            log.info("Page %d returned no events — stopping", page)
            break

        page_min_year: Optional[int] = None
        n_new = 0
        n_kept = 0

        for ev in listings:
            if ev.event_id in seen_ids:
                continue
            seen_ids.add(ev.event_id)
            n_new += 1

            if ev.year is not None:
                page_min_year = ev.year if page_min_year is None else min(page_min_year, ev.year)

            # Apply client-side filters
            if needle and needle not in ev.name.lower():
                continue
            if cat_norm:
                # For 'international' and 'regional', we need to distinguish via name classification
                if cat_norm in ("international", "regional", "challengers", "gc"):
                    if (ev.category or "").lower() != cat_norm:
                        continue
                # else cat_norm is 'all-vct' — accept anything from the VCT tier
            if year is not None and ev.year != year:
                continue
            if since_year is not None and (ev.year is None or ev.year < since_year):
                continue
            if status and (ev.status or "").lower() != status.lower():
                continue

            results.append(ev)
            n_kept += 1

            if limit is not None and len(results) >= limit:
                log.info("Hit limit (%d) — stopping", limit)
                return results

        log.info("Page %d: %d new events, %d kept after filters", page, n_new, n_kept)

        # Early-stop heuristic: if every event on this page is older than the
        # year cutoff, further pages will be older still
        if since_year is not None and page_min_year is not None and page_min_year < since_year:
            log.info("Page min year %d < since_year %d — stopping", page_min_year, since_year)
            break
        if year is not None and page_min_year is not None and page_min_year < year - 1:
            # Allow one page of slack in case events are ordered roughly by date
            log.info("Page min year %d well below target %d — stopping", page_min_year, year)
            break

    return results


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
    if event_id is None:
        return
    parsed_clean = (parsed_name or "").strip()
    if not parsed_clean or parsed_clean.lower() in _BAD_EVENT_NAMES:
        return
    event = session.get(Event, event_id)
    if event is None:
        session.add(Event(id=event_id, name=parsed_clean))
        return
    current = (event.name or "").strip().lower()
    if current in _BAD_EVENT_NAMES or event.name != parsed_clean:
        event.name = parsed_clean


def upsert_match(session: Session, detail: MatchDetail) -> Match:
    for tid, tname in (
        (detail.team_a_id, detail.team_a_name),
        (detail.team_b_id, detail.team_b_name),
    ):
        if tid is not None and not session.get(Team, tid):
            session.add(Team(id=tid, name=tname or ""))

    _upsert_event(session, detail.event_id, detail.event_name)

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
    if not listings:
        return listings, 0
    ids = [l.match_id for l in listings]
    session = get_session()
    try:
        existing = set(
            row[0] for row in session.execute(select(Match.id).where(Match.id.in_(ids))).all()
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
            log.info("Skipping %d match(es) already in DB", n_skipped)

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


def scrape_recent_results(pages: int = 1) -> int:
    """Background-friendly wrapper. Returns count of new matches inserted.

    Skips matches already in the DB (via _filter_existing inside _scrape_listings).
    Errors are caught and logged — never raised — so the caller (a scheduler
    or web request) won't crash.
    """
    try:
        result = scrape_recent(pages=pages, force=False)
        # `_scrape_listings` reports newly-persisted matches under "ok".
        return result.get("ok", 0)
    except Exception:
        log.exception("scrape_recent_results failed")
        return 0


def scrape_event(event_id: int, force: bool = False) -> dict[str, int]:
    try:
        listings = fetch_event_matches(event_id)
    except HttpError as exc:
        log.error("Failed to fetch event %d matches: %s", event_id, exc)
        return {"listed": 0, "skipped": 0, "ok": 0, "failed": 0, "player_rows": 0}
    return _scrape_listings(listings, f"event {event_id}", force=force)


def scrape_match_ids(match_ids: Iterable[int], force: bool = True) -> dict[str, int]:
    listings = [
        MatchListing(match_id=mid, url=f"{settings.vlr_base_url}/{mid}/_")
        for mid in match_ids
    ]
    return _scrape_listings(listings, f"{len(listings)} explicit match id(s)", force=force)


# --- Official vlr.gg rankings --------------------------------------------
# vlr ranks teams per region (see vlr.regions.VLR_REGION_SLUGS). We store each
# team's vlr region slug directly, so the app's regional views mirror vlr.gg
# exactly. If a team ever appears in more than one vlr region, the one scraped
# LAST wins.


def fetch_rankings_page(region_slug: str) -> str:
    return fetch(f"{settings.vlr_base_url}/rankings/{region_slug}")


def scrape_rankings(regions: Optional[list[str]] = None) -> dict[str, int]:
    """Scrape vlr.gg official team rankings and store rating / rank / record +
    the team's vlr region on each team. Safe to re-run (only updates the ranking
    columns; creates a team row only if it's brand new)."""
    slugs = regions or VLR_REGION_SLUGS
    stats = {"regions": 0, "teams": 0, "created": 0, "failed": 0}
    session = get_session()
    # team_id -> Team object, kept across regions. vlr lists some teams more
    # than once (within and across region pages); this ensures we never add the
    # same primary key twice (autoflush is off, so session.get won't return a
    # pending, not-yet-committed add).
    cache: dict[int, Team] = {}
    try:
        for slug in slugs:
            try:
                ranked: list[RankedTeam] = parse_rankings(fetch_rankings_page(slug))
            except HttpError as exc:
                log.warning("Rankings fetch failed for %s: %s", slug, exc)
                stats["failed"] += 1
                continue
            except Exception:
                log.exception("Rankings parse failed for %s", slug)
                stats["failed"] += 1
                continue

            for rt in ranked:
                team = cache.get(rt.team_id)
                if team is None:
                    team = session.get(Team, rt.team_id)
                if team is None:
                    team = Team(id=rt.team_id, name=rt.name)
                    session.add(team)
                    stats["created"] += 1
                cache[rt.team_id] = team
                if rt.name:
                    team.name = rt.name
                team.vlr_rating = rt.rating
                team.vlr_rank = rt.rank
                team.vlr_record = rt.record
                team.region = slug  # the team's vlr region
                stats["teams"] += 1
            try:
                session.commit()
            except Exception:
                session.rollback()
                cache.clear()
                log.exception("Rankings commit failed for %s", slug)
                stats["failed"] += 1
                continue
            stats["regions"] += 1
            log.info("Rankings %s: %d teams", slug, len(ranked))
    finally:
        session.close()
    return stats


# --- Bulk event scraping with resumability -------------------------------


def _read_event_id_file(filepath: Path) -> list[int]:
    ids: list[int] = []
    with filepath.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            token = line.split("#", 1)[0].strip().split()[0]
            try:
                ids.append(int(token))
            except (ValueError, IndexError):
                log.warning("Skipping unparseable line in events file: %r", raw)
    return ids


def bulk_scrape_events(
    filepath: str | Path,
    force: bool = False,
    resume: bool = True,
) -> dict[str, int]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Events file not found: {path}")

    progress_path = path.with_suffix(path.suffix + ".progress")
    progress: dict[str, dict] = {}
    if resume and progress_path.exists():
        try:
            with progress_path.open("r", encoding="utf-8") as f:
                progress = json.load(f)
            log.info("Loaded progress from %s (%d entries)", progress_path, len(progress))
        except (json.JSONDecodeError, OSError):
            log.warning("Could not read progress file, starting fresh")
            progress = {}

    event_ids = _read_event_id_file(path)
    log.info("Bulk-scraping %d events from %s", len(event_ids), path)

    summary = {
        "events_total": len(event_ids),
        "events_skipped_done": 0,
        "events_ok": 0,
        "events_failed": 0,
        "matches_ok": 0,
        "matches_failed": 0,
        "player_rows": 0,
    }

    for idx, event_id in enumerate(event_ids, start=1):
        key = str(event_id)
        prior = progress.get(key)
        if resume and prior and prior.get("status") == "ok" and not force:
            log.info("[%d/%d] Skipping event %d (already done)", idx, len(event_ids), event_id)
            summary["events_skipped_done"] += 1
            continue

        log.info("[%d/%d] Scraping event %d ...", idx, len(event_ids), event_id)
        try:
            stats = scrape_event(event_id, force=force)
            progress[key] = {
                "status": "ok",
                "matches_ok": stats["ok"],
                "matches_failed": stats["failed"],
                "player_rows": stats["player_rows"],
            }
            summary["events_ok"] += 1
            summary["matches_ok"] += stats["ok"]
            summary["matches_failed"] += stats["failed"]
            summary["player_rows"] += stats["player_rows"]
        except Exception as exc:
            log.exception("Event %d failed entirely", event_id)
            progress[key] = {"status": "failed", "error": str(exc)}
            summary["events_failed"] += 1

        try:
            with progress_path.open("w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2)
        except OSError:
            log.warning("Could not write progress file")

    return summary


# --- Maintenance ----------------------------------------------------------


def repair_event_names() -> dict[str, int]:
    stats = {"checked": 0, "fixed": 0, "no_match": 0, "failed": 0}
    session = get_session()
    try:
        bad_events = (
            session.execute(
                select(Event).where(
                    Event.name.in_(["upcoming", "completed", "live", "final", "tbd", "ongoing", ""])
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
                stats["failed"] += 1
    finally:
        session.close()
    return stats


# --- Player profile backfill (Iteration 9 Drop 2) ---------------------------


def fetch_player_profile(player_id: int):
    """Fetch and parse a single player profile page from vlr.gg.

    Returns a PlayerProfile dataclass, or None if the page couldn't be fetched.
    Profile fields can still be None individually if vlr.gg's HTML didn't match
    our selectors — caller should handle that gracefully.
    """
    from .parsers import parse_player_profile, PlayerProfile
    # vlr.gg redirects /player/{id} to /player/{id}/{slug} automatically.
    # Trailing slug doesn't matter — vlr.gg matches by ID.
    url = f"https://www.vlr.gg/player/{player_id}/_"
    try:
        html = fetch(url)
    except HttpError as exc:
        log.error("Failed to fetch player %d: %s", player_id, exc)
        return None
    return parse_player_profile(html, player_id)


def fetch_team_profile(team_id: int):
    """Fetch and parse a team profile page. Returns TeamProfile or None."""
    from .parsers import parse_team_profile
    url = f"https://www.vlr.gg/team/{team_id}/_"
    try:
        html = fetch(url)
    except HttpError as exc:
        log.error("Failed to fetch team %d: %s", team_id, exc)
        return None
    return parse_team_profile(html, team_id)


def save_player_profile(profile, force: bool = False) -> bool:
    """Persist a PlayerProfile. Returns True if the row was updated.

    By default skips rows that already have an image_url to support resumable
    backfills. Pass force=True to overwrite.
    """
    session = get_session()
    try:
        player = session.get(Player, profile.player_id)
        if player is None:
            return False
        if player.image_url and not force:
            # Already populated — leave it alone.
            return False
        # Only set fields we successfully parsed; never overwrite with None.
        updated = False
        if profile.image_url:
            player.image_url = profile.image_url
            updated = True
        if profile.country:
            player.country = profile.country
            updated = True
        if profile.real_name:
            player.real_name = profile.real_name
            updated = True
        if updated:
            session.commit()
        return updated
    finally:
        session.close()


def save_team_profile(profile, force: bool = False) -> bool:
    """Persist a TeamProfile. Skips already-populated rows by default."""
    session = get_session()
    try:
        team = session.get(Team, profile.team_id)
        if team is None:
            return False
        if team.logo_url and not force:
            return False
        updated = False
        if profile.logo_url:
            team.logo_url = profile.logo_url
            updated = True
        if profile.country:
            team.country = profile.country
            updated = True
        if updated:
            session.commit()
        return updated
    finally:
        session.close()


def backfill_player_profiles(
    limit: Optional[int] = None,
    force: bool = False,
    on_progress=None,
) -> dict[str, int]:
    """Iterate every player and scrape their vlr.gg profile.

    Skips players who already have an image_url (resumable across crashes).
    Pass force=True to re-scrape everyone.

    `on_progress` is called as `on_progress(index, total, player_id, status)`
    after each player so the CLI can render a live progress bar.
    """
    session = get_session()
    try:
        # Order by id so progress is predictable across runs.
        query = session.execute(
            select(Player.id, Player.image_url).order_by(Player.id.asc())
        )
        rows = [(pid, img) for pid, img in query.all()]
    finally:
        session.close()

    todo = rows if force else [(pid, img) for pid, img in rows if not img]
    if limit:
        todo = todo[:limit]

    counts = {"attempted": 0, "updated": 0, "failed": 0, "no_data": 0,
              "skipped": len(rows) - len(todo)}
    total = len(todo)

    for i, (pid, _) in enumerate(todo, start=1):
        counts["attempted"] += 1
        try:
            profile = fetch_player_profile(pid)
            if profile is None:
                counts["failed"] += 1
                status = "failed"
            elif profile.image_url is None and profile.country is None:
                counts["no_data"] += 1
                status = "no_data"
            else:
                if save_player_profile(profile, force=force):
                    counts["updated"] += 1
                    status = "ok"
                else:
                    counts["no_data"] += 1
                    status = "no_data"
        except Exception:
            log.exception("Unexpected error scraping player %d", pid)
            counts["failed"] += 1
            status = "failed"

        if on_progress:
            on_progress(i, total, pid, status)

    return counts


def backfill_team_logos(
    limit: Optional[int] = None,
    force: bool = False,
    on_progress=None,
) -> dict[str, int]:
    """Same as backfill_player_profiles but for team logos."""
    session = get_session()
    try:
        query = session.execute(
            select(Team.id, Team.logo_url).order_by(Team.id.asc())
        )
        rows = [(tid, logo) for tid, logo in query.all()]
    finally:
        session.close()

    todo = rows if force else [(tid, logo) for tid, logo in rows if not logo]
    if limit:
        todo = todo[:limit]

    counts = {"attempted": 0, "updated": 0, "failed": 0, "no_data": 0,
              "skipped": len(rows) - len(todo)}
    total = len(todo)

    for i, (tid, _) in enumerate(todo, start=1):
        counts["attempted"] += 1
        try:
            profile = fetch_team_profile(tid)
            if profile is None:
                counts["failed"] += 1
                status = "failed"
            elif profile.logo_url is None:
                counts["no_data"] += 1
                status = "no_data"
            else:
                if save_team_profile(profile, force=force):
                    counts["updated"] += 1
                    status = "ok"
                else:
                    counts["no_data"] += 1
                    status = "no_data"
        except Exception:
            log.exception("Unexpected error scraping team %d", tid)
            counts["failed"] += 1
            status = "failed"

        if on_progress:
            on_progress(i, total, tid, status)

    return counts


# --- Full refresh cycle ---------------------------------------------------
# One call that keeps everything aligned with vlr. Every step is incremental:
# matches skip ones already in the DB; profile/logo backfills skip rows that are
# already populated; rankings + tier classification just overwrite with fresh
# values (cheap). So re-running only does work for NEW / changed data.


def _classify_event_tiers() -> int:
    """(Re)classify every event's tier from its name. Cheap, no network."""
    from ..ml.tiers import classify_event_tier
    session = get_session()
    try:
        events = session.execute(select(Event)).scalars().all()
        changed = 0
        for ev in events:
            tier = classify_event_tier(ev.name)
            if ev.tier != tier:
                ev.tier = tier
                changed += 1
        session.commit()
        return changed
    finally:
        session.close()


# How many player photos / team logos to top up per refresh. Bounded so a single
# refresh can't run for hours at ~2s/request — it just keeps chipping at the
# trickle of NEW players/teams. Clear a big historical backlog once, by hand,
# with `python -m vlr.cli backfill-player-profiles` (no limit).
REFRESH_PROFILE_LIMIT = 80
REFRESH_LOGO_LIMIT = 50


def run_full_refresh(pages: int = 1) -> dict:
    """Full data-refresh: new matches + vlr rankings + new player photos +
    new team logos + event tiers. Each step is incremental (see note above).
    The photo/logo top-ups are capped per run so this never runs for hours."""
    result: dict = {}

    try:
        result["new_matches"] = scrape_recent_results(pages=pages)
    except Exception:
        log.exception("full-refresh: recent matches failed")
        result["new_matches"] = 0

    try:
        result["rankings"] = scrape_rankings()
    except Exception:
        log.exception("full-refresh: rankings failed")
        result["rankings"] = {}

    try:
        result["player_profiles"] = backfill_player_profiles(limit=REFRESH_PROFILE_LIMIT)
    except Exception:
        log.exception("full-refresh: player profiles failed")
        result["player_profiles"] = {}

    try:
        result["team_logos"] = backfill_team_logos(limit=REFRESH_LOGO_LIMIT)
    except Exception:
        log.exception("full-refresh: team logos failed")
        result["team_logos"] = {}

    try:
        result["events_reclassified"] = _classify_event_tiers()
    except Exception:
        log.exception("full-refresh: tier classify failed")
        result["events_reclassified"] = 0

    # Prediction track record: pull upcoming matches, predict them, and link
    # results for any predicted match that has since completed.
    try:
        result["upcoming_scraped"] = scrape_upcoming()
    except Exception:
        log.exception("full-refresh: scrape upcoming failed")
        result["upcoming_scraped"] = 0

    try:
        from ..ml.track_record import link_results, predict_upcoming
        result["predictions_made"] = predict_upcoming()
        result["predictions_linked"] = link_results()
    except Exception:
        log.exception("full-refresh: predictions failed")

    log.info("full-refresh complete: %s", result)
    return result
