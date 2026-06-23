"""HTML parsers for vlr.gg pages.

Selectors here are based on the actual class names vlr.gg uses. The most
important structural facts:

- Per-map stats live inside `div.vm-stats-container > div.vm-stats-game[data-game-id]`
- The event name lives in `div.match-header-super` (NOT the status badge at the
  top of the page, which is also a link to the event URL but contains the text
  "upcoming"/"completed"/"live").

If vlr.gg changes its HTML, this is the only file you should need to edit.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

log = logging.getLogger(__name__)

# --- URL patterns ----------------------------------------------------------

MATCH_URL_RE = re.compile(r"^/(\d+)/[a-z0-9\-]+(?:/.*)?$", re.IGNORECASE)
TEAM_URL_RE = re.compile(r"^/team/(\d+)/[a-z0-9\-]+/?$", re.IGNORECASE)
EVENT_URL_RE = re.compile(r"^/event/(\d+)/[a-z0-9\-]+(?:/.*)?$", re.IGNORECASE)
PLAYER_URL_RE = re.compile(r"^/player/(\d+)/[a-z0-9\-]+/?$", re.IGNORECASE)

# Words that appear as the *text* of a link to an event URL but are status
# badges, not the actual event name.
_STATUS_WORDS = {"upcoming", "completed", "live", "final", "tbd", ""}


# --- Dataclasses -----------------------------------------------------------


@dataclass
class MatchListing:
    match_id: int
    url: str


@dataclass
class VetoAction:
    order_index: int
    team_name: Optional[str]
    action: str  # 'ban' | 'pick' | 'decider'
    map_name: str


@dataclass
class PlayerStat:
    """Per-map performance for one player."""

    player_id: int
    player_name: str
    team_name: Optional[str] = None
    team_index: Optional[int] = None
    agent: Optional[str] = None
    rating: Optional[float] = None
    acs: Optional[int] = None
    kills: Optional[int] = None
    deaths: Optional[int] = None
    assists: Optional[int] = None
    plus_minus: Optional[int] = None
    kast: Optional[int] = None
    adr: Optional[float] = None
    hs_pct: Optional[int] = None
    fk: Optional[int] = None
    fd: Optional[int] = None
    fk_fd_diff: Optional[int] = None


@dataclass
class MapResult:
    map_index: int
    map_name: str
    score_a: Optional[int]
    score_b: Optional[int]
    picked_by: Optional[str] = None
    player_stats: list[PlayerStat] = field(default_factory=list)


@dataclass
class MatchDetail:
    match_id: int
    url: str
    team_a_id: Optional[int]
    team_b_id: Optional[int]
    team_a_name: str
    team_b_name: str
    score_a: Optional[int]
    score_b: Optional[int]
    best_of: Optional[int]
    event_id: Optional[int]
    event_name: Optional[str]
    stage: Optional[str]
    patch: Optional[str]
    match_datetime: Optional[datetime]
    veto_raw: Optional[str]
    veto_actions: list[VetoAction] = field(default_factory=list)
    maps: list[MapResult] = field(default_factory=list)


# --- Helpers ---------------------------------------------------------------


def _absolute(base_url: str, href: str) -> str:
    if href.startswith("http"):
        return href
    return f"{base_url.rstrip('/')}{href}"


def _strip(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    cleaned = " ".join(text.split())
    return cleaned or None


def _first_token(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    tokens = cleaned.split()
    return tokens[0] if tokens else None


def _int_or_none(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    text = text.strip()
    if not text or not text.lstrip("-+").isdigit():
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _float_or_none(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    cleaned = text.strip().rstrip("%")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _percent_or_none(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    cleaned = text.strip().rstrip("%").strip()
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except (TypeError, ValueError):
        return None


# --- Parser: results listing ----------------------------------------------


def parse_results_listing(html: str, base_url: str) -> list[MatchListing]:
    soup = BeautifulSoup(html, "lxml")
    seen: dict[int, MatchListing] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = MATCH_URL_RE.match(href)
        if not m:
            continue
        match_id = int(m.group(1))
        if match_id in seen:
            continue
        seen[match_id] = MatchListing(
            match_id=match_id,
            url=_absolute(base_url, href.split("?", 1)[0]),
        )
    log.info("Found %d unique matches on results page", len(seen))
    return list(seen.values())


# --- Parser: match detail --------------------------------------------------


def _extract_event_info(soup: BeautifulSoup) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Return (event_id, event_name, stage) from the match detail page.

    The reliable place to get this is `div.match-header-super`, which contains
    a single <a> linking to the event page. Inside the anchor is a container
    <div> with two child divs: event name and stage label.

    We avoid grabbing the *first* link to /event/<id>/ on the page because
    that link wraps a status badge ("upcoming"/"completed"/"live") and its
    text is the status word, not the event name.
    """
    super_header = soup.find("div", class_=re.compile(r"\bmatch-header-super\b"))
    if super_header is not None:
        a = super_header.find("a", href=EVENT_URL_RE)
        if a is not None:
            m = EVENT_URL_RE.match(a["href"])
            event_id = int(m.group(1)) if m else None
            container = a.find("div")
            inner = container.find_all("div", recursive=False) if container else []
            event_name = _strip(inner[0].get_text()) if len(inner) >= 1 else None
            stage = _strip(inner[1].get_text()) if len(inner) >= 2 else None
            if event_name and event_name.lower() not in _STATUS_WORDS:
                return event_id, event_name, stage

    # Fallback: scan all event-link anchors, skip status badges, prefer the
    # longest non-status-word text.
    candidates: list[tuple[int, str]] = []
    for a in soup.find_all("a", href=EVENT_URL_RE):
        m = EVENT_URL_RE.match(a["href"])
        if not m:
            continue
        text = _strip(a.get_text())
        if not text or text.lower() in _STATUS_WORDS:
            continue
        if len(text) < 5:
            continue
        candidates.append((int(m.group(1)), text))

    if candidates:
        # Pick the longest text — usually the actual descriptive event name
        eid, name = max(candidates, key=lambda p: len(p[1]))
        return eid, name, None

    return None, None, None


_PATCH_RE = re.compile(r"Patch\s+([0-9]+\.[0-9]+)", re.IGNORECASE)
_BO_RE = re.compile(r"\bBo([135])\b", re.IGNORECASE)
_VETO_BAN_RE = re.compile(r"^([\w\s\-\.\u00C0-\u024F]+?)\s+(ban|pick)\s+(.+)$", re.IGNORECASE)
_VETO_DECIDER_RE = re.compile(r"^(.+?)\s+(remains|decider)$", re.IGNORECASE)


def _find_veto_text(soup: BeautifulSoup) -> Optional[str]:
    veto_node = soup.find("div", class_=re.compile(r"match-header-note"))
    if veto_node:
        text = _strip(veto_node.get_text())
        if text and ";" in text:
            return text

    for el in soup.find_all(string=True):
        s = _strip(str(el))
        if not s:
            continue
        lo = s.lower()
        has_ban_or_pick = " ban " in lo or " pick " in lo
        has_terminator = "remains" in lo or "decider" in lo or lo.count("ban") + lo.count("pick") >= 4
        if ";" in s and has_ban_or_pick and has_terminator:
            return s
    return None


def parse_veto(veto_raw: str) -> list[VetoAction]:
    actions: list[VetoAction] = []
    for idx, raw_chunk in enumerate(veto_raw.split(";")):
        chunk = _strip(raw_chunk)
        if not chunk:
            continue
        m = _VETO_BAN_RE.match(chunk)
        if m:
            actions.append(
                VetoAction(
                    order_index=idx,
                    team_name=_strip(m.group(1)),
                    action=m.group(2).lower(),
                    map_name=_strip(m.group(3)) or "",
                )
            )
            continue
        m = _VETO_DECIDER_RE.match(chunk)
        if m:
            actions.append(
                VetoAction(
                    order_index=idx,
                    team_name=None,
                    action="decider",
                    map_name=_strip(m.group(1)) or "",
                )
            )
            continue
        log.warning("Unrecognised veto chunk: %r", chunk)
    return actions


_MAP_POOL = {
    "abyss", "ascent", "bind", "breeze", "fracture", "haven",
    "icebox", "lotus", "pearl", "split", "sunset", "corrode",
}


# --- Per-player stat extraction --------------------------------------------


def _extract_team_tag(row: Tag, player_name: Optional[str]) -> Optional[str]:
    team_node = row.find(class_=re.compile(r"ge-text-light|stats-sq"))
    if team_node:
        tag = _strip(team_node.get_text())
        if tag and tag != player_name:
            return tag

    a = row.find("a", href=PLAYER_URL_RE)
    if a:
        full_text = _strip(a.get_text()) or ""
        if player_name and full_text.startswith(player_name):
            remainder = _strip(full_text[len(player_name):])
            if remainder:
                return remainder
        tokens = full_text.split()
        if len(tokens) >= 2:
            return tokens[-1]
    return None


def _extract_agent(row: Tag) -> Optional[str]:
    cells = row.find_all("td")
    candidate_cells = []
    if len(cells) >= 2:
        candidate_cells.append(cells[1])
    candidate_cells.append(row)

    for cell in candidate_cells:
        img = cell.find("img")
        if img is None:
            continue
        for attr in ("alt", "title"):
            value = img.get(attr)
            if value:
                value = value.strip().lower()
                if value:
                    return value
        src = img.get("src", "")
        m = re.search(r"/agents/([a-zA-Z0-9_\-]+)\.(?:png|webp|jpg)", src)
        if m:
            return m.group(1).lower()
    return None


def _cell_value(cell: Tag) -> Optional[str]:
    if cell is None:
        return None
    both = cell.find("span", class_=re.compile(r"\bmod-both\b|\bside-both\b"))
    if both:
        text = _first_token(both.get_text())
        if text:
            return text
    text = cell.get_text(" ", strip=True)
    for token in text.split():
        stripped = token.rstrip("%").lstrip("+-")
        if stripped and stripped.replace(".", "", 1).isdigit():
            return token
    return None


def _parse_player_row(row: Tag, team_index: int) -> Optional[PlayerStat]:
    a = row.find("a", href=PLAYER_URL_RE)
    if a is None:
        return None
    href_match = PLAYER_URL_RE.match(a.get("href", ""))
    if not href_match:
        return None
    player_id = int(href_match.group(1))

    name_node = row.find("div", class_=re.compile(r"text-of"))
    player_name = _first_token(name_node.get_text()) if name_node else _first_token(a.get_text())
    if not player_name:
        return None

    team_tag = _extract_team_tag(row, player_name)
    agent = _extract_agent(row)

    cells = row.find_all("td")
    if len(cells) < 3:
        return None

    return PlayerStat(
        player_id=player_id,
        player_name=player_name,
        team_name=team_tag,
        team_index=team_index,
        agent=agent,
        rating=_float_or_none(_cell_value(cells[2]) if len(cells) > 2 else None),
        acs=_int_or_none(_cell_value(cells[3]) if len(cells) > 3 else None),
        kills=_int_or_none(_cell_value(cells[4]) if len(cells) > 4 else None),
        deaths=_int_or_none(_cell_value(cells[5]) if len(cells) > 5 else None),
        assists=_int_or_none(_cell_value(cells[6]) if len(cells) > 6 else None),
        plus_minus=_int_or_none(_cell_value(cells[7]) if len(cells) > 7 else None),
        kast=_percent_or_none(_cell_value(cells[8]) if len(cells) > 8 else None),
        adr=_float_or_none(_cell_value(cells[9]) if len(cells) > 9 else None),
        hs_pct=_percent_or_none(_cell_value(cells[10]) if len(cells) > 10 else None),
        fk=_int_or_none(_cell_value(cells[11]) if len(cells) > 11 else None),
        fd=_int_or_none(_cell_value(cells[12]) if len(cells) > 12 else None),
        fk_fd_diff=_int_or_none(_cell_value(cells[13]) if len(cells) > 13 else None),
    )


def _extract_player_stats(block: Tag) -> list[PlayerStat]:
    stats: list[PlayerStat] = []
    tbodies = block.find_all("tbody")
    for team_index, tbody in enumerate(tbodies[:2]):
        for row in tbody.find_all("tr"):
            stat = _parse_player_row(row, team_index=team_index)
            if stat is not None:
                stats.append(stat)
    return stats


def _extract_map_score(score_div: Tag) -> Optional[int]:
    if score_div is None:
        return None
    raw = score_div.get_text(" ", strip=True)
    token = _first_token(raw)
    return _int_or_none(token)


def _parse_maps(soup: BeautifulSoup) -> list[MapResult]:
    results: list[MapResult] = []
    seen_names: set[str] = set()

    container = soup.find("div", class_=re.compile(r"\bvm-stats-container\b"))
    if container is None:
        log.warning("No div.vm-stats-container found — falling back to global scan.")
        candidates = soup.find_all("div", class_=re.compile(r"\bvm-stats-game\b"))
        blocks = [b for b in candidates if b.find("tbody") is not None]
    else:
        blocks = container.find_all("div", class_=re.compile(r"\bvm-stats-game\b"))

    for block in blocks:
        game_id = block.get("data-game-id", "")
        if game_id == "all":
            continue

        map_node = block.find("div", class_=re.compile(r"\bmap\b"))
        if map_node is None:
            continue
        map_text = _strip(map_node.get_text()) or ""
        map_name_raw = _first_token(map_text) or ""
        if not map_name_raw or map_name_raw.lower() == "tbd":
            continue
        if map_name_raw.lower() in _MAP_POOL:
            map_name = map_name_raw.lower().capitalize()
        else:
            map_name = map_name_raw
        if map_name in seen_names:
            continue
        seen_names.add(map_name)

        score_divs = block.find_all("div", class_=re.compile(r"\bscore\b"))
        score_a = _extract_map_score(score_divs[0]) if len(score_divs) >= 1 else None
        score_b = _extract_map_score(score_divs[1]) if len(score_divs) >= 2 else None

        player_stats = _extract_player_stats(block)

        results.append(
            MapResult(
                map_index=len(results) + 1,
                map_name=map_name,
                score_a=score_a,
                score_b=score_b,
                player_stats=player_stats,
            )
        )

    return results


def parse_match_detail(html: str, match_url: str) -> MatchDetail:
    soup = BeautifulSoup(html, "lxml")

    path = match_url.split("?", 1)[0].rstrip("/")
    m = re.search(r"/(\d+)/", path)
    if not m:
        raise ValueError(f"Could not extract match id from URL: {match_url}")
    match_id = int(m.group(1))

    # Teams
    team_a_id = team_b_id = None
    team_a_name = team_b_name = ""
    header = soup.find("div", class_=re.compile(r"match-header-vs"))
    if header is not None:
        link_a = header.find("a", class_=re.compile(r"match-header-link.*mod-1"))
        link_b = header.find("a", class_=re.compile(r"match-header-link.*mod-2"))
        for link, side in ((link_a, "a"), (link_b, "b")):
            if link is None:
                continue
            href = link.get("href", "")
            tm = TEAM_URL_RE.match(href)
            tid = int(tm.group(1)) if tm else None
            name_node = link.find("div", class_=re.compile(r"match-header-link-name|wf-title-med"))
            if name_node is None:
                name_node = link
            tname = _strip(name_node.get_text()) or ""
            tname = re.split(r"\s+\[", tname)[0].strip()
            if side == "a":
                team_a_id, team_a_name = tid, tname
            else:
                team_b_id, team_b_name = tid, tname

    if not team_a_name or not team_b_name:
        seen_ids: dict[int, str] = {}
        for a in soup.find_all("a", href=TEAM_URL_RE):
            mid = TEAM_URL_RE.match(a["href"])
            if not mid:
                continue
            tid = int(mid.group(1))
            name = _strip(a.get_text())
            if tid not in seen_ids and name:
                seen_ids[tid] = name
            if len(seen_ids) >= 2:
                break
        ordered = list(seen_ids.items())
        if len(ordered) >= 2:
            if team_a_id is None:
                team_a_id, team_a_name = ordered[0]
            if team_b_id is None:
                team_b_id, team_b_name = ordered[1]

    # Event + stage (both now from match-header-super)
    event_id, event_name, stage_from_event = _extract_event_info(soup)

    # Match score
    score_a = score_b = None
    score_nodes = soup.select(".match-header-vs-score .js-spoiler span")
    score_ints = [_int_or_none(_strip(n.get_text())) for n in score_nodes]
    score_ints = [s for s in score_ints if s is not None]
    if len(score_ints) >= 2:
        score_a, score_b = score_ints[0], score_ints[-1]

    page_text = soup.get_text(" ", strip=True)
    best_of = int(_BO_RE.search(page_text).group(1)) if _BO_RE.search(page_text) else None
    patch = _PATCH_RE.search(page_text).group(1) if _PATCH_RE.search(page_text) else None

    # Stage: prefer the second div from event link, fall back to match-header-event-series
    stage = stage_from_event
    if not stage:
        stage_node = soup.find(class_=re.compile(r"match-header-event-series"))
        if stage_node:
            stage = _strip(stage_node.get_text())

    match_datetime = None
    moment_node = soup.find(attrs={"data-utc-ts": True})
    if moment_node:
        try:
            match_datetime = datetime.fromisoformat(moment_node["data-utc-ts"].replace(" ", "T"))
        except (ValueError, TypeError):
            match_datetime = None

    veto_raw = _find_veto_text(soup)
    veto_actions = parse_veto(veto_raw) if veto_raw else []

    maps = _parse_maps(soup)

    picker_lookup = {v.map_name: v.team_name for v in veto_actions if v.action == "pick"}
    for m_result in maps:
        if m_result.map_name in picker_lookup:
            m_result.picked_by = picker_lookup[m_result.map_name]
        elif any(v.action == "decider" and v.map_name == m_result.map_name for v in veto_actions):
            m_result.picked_by = "decider"

    return MatchDetail(
        match_id=match_id,
        url=match_url,
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        team_a_name=team_a_name or "",
        team_b_name=team_b_name or "",
        score_a=score_a,
        score_b=score_b,
        best_of=best_of,
        event_id=event_id,
        event_name=event_name,
        stage=stage,
        patch=patch,
        match_datetime=match_datetime,
        veto_raw=veto_raw,
        veto_actions=veto_actions,
        maps=maps,
    )
