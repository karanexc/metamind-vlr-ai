"""HTML parsers for vlr.gg pages.

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

_STATUS_WORDS = {"upcoming", "completed", "live", "final", "tbd", "ongoing", ""}


# --- Dataclasses -----------------------------------------------------------


@dataclass
class MatchListing:
    match_id: int
    url: str


@dataclass
class EventListing:
    """One event card from /events listings."""

    event_id: int
    name: str
    url: str
    category: Optional[str] = None     # 'international', 'regional', 'challengers', 'gc', 'other'
    status: Optional[str] = None       # 'completed' / 'ongoing' / 'upcoming'
    region: Optional[str] = None       # 'americas', 'emea', 'pacific', 'cn', 'global'
    date_range: Optional[str] = None
    year: Optional[int] = None
    prize_pool: Optional[str] = None


@dataclass
class VetoAction:
    order_index: int
    team_name: Optional[str]
    action: str
    map_name: str


@dataclass
class PlayerStat:
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


_YEAR_RE = re.compile(r"\b(20[2-3]\d)\b")
_DATE_RE = re.compile(r"[A-Z][a-z]{2,3}\s+\d{1,2}", re.IGNORECASE)
_PRIZE_RE = re.compile(r"\$[\d,]+(?:\.\d+)?|^TBD$")


def _infer_year(name: str, url: str, date_range: Optional[str]) -> Optional[int]:
    for source in (name, url, date_range or ""):
        m = _YEAR_RE.search(source)
        if m:
            return int(m.group(1))
    return None


# Region detection from event name (vlr.gg doesn't always have a flag image)
_REGION_NAME_HINTS = [
    # most specific first
    (re.compile(r"\b(americas|amer|na\b|north\s+america|latam|brazil|brasil|braza|mexico|argentina|colombia)\b", re.I), "americas"),
    (re.compile(r"\b(emea|europe\b|eu\b|mena|t[uü]rkiye|turkey|spain|france|dach|nordic|denmark|italy|uk|germany|poland|czech|portugal|africa)\b", re.I), "emea"),
    (re.compile(r"\b(pacific|pac|sea\b|southeast\s+asia|japan|korea|jp\b|kr\b|south\s+asia|oce|oceania|wave|philippines|thailand|vietnam|indonesia|singapore)\b", re.I), "pacific"),
    (re.compile(r"\b(china|chinese|cn\b)\b", re.I), "cn"),
    (re.compile(r"\b(global|international|world|invitational)\b", re.I), "global"),
]


def _region_from_name(name: str) -> Optional[str]:
    for pattern, mapped in _REGION_NAME_HINTS:
        if pattern.search(name):
            return mapped
    return None


# Name-based category classification — more reliable than vlr.gg's per-card markup
_INTERNATIONAL_PATTERNS = [
    re.compile(r"\bvalorant\s+masters\b", re.I),
    re.compile(r"\bvalorant\s+champions\b", re.I),
    re.compile(r"\bchampions\s+tour\b.*\bmasters\b", re.I),
    re.compile(r"\bchampions\s+tour\b.*\bchampions\b", re.I),
    re.compile(r"\bvct\s+kickoff\b", re.I),
    re.compile(r"\bgame\s+changers\s+championship\b", re.I),
    re.compile(r"\bvct.*stage\s+\d.*global", re.I),
]
_REGIONAL_PATTERNS = [
    re.compile(r"\bvct\s+\d{4}:\s*(americas|emea|pacific|china)\b.*stage", re.I),
    re.compile(r"\bchampions\s+tour\s+\d{4}:\s*(americas|emea|pacific|china)\s+stage", re.I),
    re.compile(r"\bvct\s+\d{4}:\s*(americas|emea|pacific|china)", re.I),
    re.compile(r"\bchampions\s+tour\s+\d{4}:\s*(americas|emea|pacific|china)", re.I),
]
_CHALLENGERS_PATTERNS = [
    re.compile(r"\bchallengers\s+\d{4}\b", re.I),
    re.compile(r"\bvcl\b", re.I),
]
_GC_PATTERNS = [
    re.compile(r"\bgame\s+changers\b", re.I),
]


def _classify_event_name(name: str) -> str:
    for pat in _INTERNATIONAL_PATTERNS:
        if pat.search(name):
            return "international"
    for pat in _REGIONAL_PATTERNS:
        if pat.search(name):
            return "regional"
    for pat in _CHALLENGERS_PATTERNS:
        if pat.search(name):
            return "challengers"
    for pat in _GC_PATTERNS:
        if pat.search(name):
            return "gc"
    return "other"


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


# --- Parser: events listing -----------------------------------------------


def _extract_event_from_anchor(a: Tag, base_url: str) -> Optional[EventListing]:
    """Each event 'card' on /events is itself an <a> tag.

    The anchor's text content has a predictable structure:
        Line 1: Event name
        Line 2: status (ongoing/completed/upcoming)
        Line 3: "Status" label
        Line 4: prize pool value ($XXX or TBD)
        Line 5: "Prize Pool" label
        Line 6: dates (e.g. "Apr 2—May 17")
        Line 7: "Dates" label
        Line 8: "Region" label (the actual flag is an <img>)
    """
    m = EVENT_URL_RE.match(a.get("href", ""))
    if not m:
        return None
    event_id = int(m.group(1))
    href = a["href"].split("?", 1)[0]
    url = _absolute(base_url, href)

    text = a.get_text(separator="\n")
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return None

    # First line is the event name
    name = lines[0]
    if len(name) < 3:
        return None

    # Status: a standalone line matching one of the status words
    status = None
    for line in lines[1:6]:
        low = line.lower()
        if low in ("ongoing", "completed", "upcoming", "live"):
            status = low
            break

    # Prize pool: line that's a $ amount or "TBD" appearing before "Prize Pool" label
    prize_pool = None
    for i, line in enumerate(lines):
        if _PRIZE_RE.match(line):
            # Verify by checking the next line is the label (or just trust the match)
            prize_pool = line
            break

    # Dates: line matching "Apr 2" or "Apr 2—May 17" patterns
    date_range = None
    for line in lines:
        if _DATE_RE.search(line) and ("—" in line or "-" in line or line.count(" ") <= 3):
            # Avoid picking up the event name if it contains a date-like substring
            if line == name:
                continue
            date_range = line
            break

    # Region from the flag image if present (vlr.gg loads team-specific or
    # region flag images near the end of the card)
    region = None
    for img in a.find_all("img"):
        alt = (img.get("alt") or "").lower()
        if alt in ("americas", "emea", "pacific", "china"):
            region = alt
            break
    if not region:
        region = _region_from_name(name)

    category = _classify_event_name(name)
    year = _infer_year(name, url, date_range)

    return EventListing(
        event_id=event_id,
        name=name,
        url=url,
        category=category,
        status=status,
        region=region,
        date_range=date_range,
        year=year,
        prize_pool=prize_pool,
    )


def parse_events_listing(html: str, base_url: str) -> list[EventListing]:
    """Parse an /events page into a list of EventListings.

    Each event 'card' on vlr.gg is a single <a> tag — we just iterate every
    anchor that points to /event/<id>/<slug> and extract structured data
    from its text content.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: dict[int, EventListing] = {}

    for a in soup.find_all("a", href=EVENT_URL_RE):
        listing = _extract_event_from_anchor(a, base_url)
        if listing is None:
            continue
        if listing.event_id in seen:
            continue
        seen[listing.event_id] = listing

    log.info("Found %d unique events on page", len(seen))
    return list(seen.values())


# --- Parser: match detail (unchanged) ------------------------------------


def _extract_event_info(soup: BeautifulSoup) -> tuple[Optional[int], Optional[str], Optional[str]]:
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


def _cls_str(el: Tag) -> str:
    c = el.get("class") or []
    return " ".join(c) if isinstance(c, list) else str(c)


def _both_cell_value(cell: Tag) -> Optional[str]:
    """Value from a new-layout stat cell — prefer the combined `.side.mod-both`
    span, else the first numeric-ish token in the cell."""
    if cell is None:
        return None
    both = cell.select_one(".side.mod-both")
    if both is not None:
        text = _strip(both.get_text())
        if text:
            return text
    text = cell.get_text(" ", strip=True)
    for token in text.split():
        stripped = token.rstrip("%").lstrip("+-")
        if stripped and stripped.replace(".", "", 1).isdigit():
            return token
    return _strip(text)


def _parse_player_cell_div(
    player_cell: Tag, stat_cells: list[Tag], team_index: int
) -> Optional[PlayerStat]:
    """Parse one player from vlr's new div layout: a `.ovw-cell.mod-player`
    (name + agent) followed by stat cells keyed by `data-col`. The `kills` cell
    is `.mod-kda` and holds K/D/A in `.ovw-kda-stat` sub-elements."""
    a = player_cell.find("a", href=PLAYER_URL_RE)
    if a is None:
        return None
    m = PLAYER_URL_RE.match(a.get("href", ""))
    if not m:
        return None
    player_id = int(m.group(1))

    name_node = player_cell.select_one(".ovw-player-name")
    player_name = _strip(name_node.get_text()) if name_node else _strip(a.get_text())
    if not player_name:
        return None

    tag_node = player_cell.select_one(".ovw-player-tag")
    team_tag = _strip(tag_node.get_text()) if tag_node else None

    agent = None
    agent_img = player_cell.select_one(".ovw-agents img")
    if agent_img is not None:
        agent = (agent_img.get("title") or agent_img.get("alt") or "").strip().lower() or None
        if not agent:
            am = re.search(r"/agents/([a-zA-Z0-9_\-]+)\.(?:png|webp|jpg)", agent_img.get("src", ""))
            if am:
                agent = am.group(1).lower()

    values: dict[str, Optional[str]] = {}
    kills = deaths = assists = None
    for cell in stat_cells:
        if "mod-kda" in _cls_str(cell):
            for ks in cell.select(".ovw-kda-stat"):
                kdc = ks.get("data-col", "")
                both = ks.select_one(".side.mod-both")
                val = _strip(both.get_text()) if both else _strip(ks.get_text())
                if kdc == "kills":
                    kills = val
                elif kdc == "deaths":
                    deaths = val
                elif kdc == "assists":
                    assists = val
            continue
        data_col = cell.get("data-col", "")
        if data_col:
            values[data_col] = _both_cell_value(cell)

    return PlayerStat(
        player_id=player_id,
        player_name=player_name,
        team_name=team_tag,
        team_index=team_index,
        agent=agent,
        rating=_float_or_none(values.get("rating2")),
        acs=_int_or_none(values.get("acs")),
        kills=_int_or_none(kills),
        deaths=_int_or_none(deaths),
        assists=_int_or_none(assists),
        plus_minus=_int_or_none(values.get("kd-diff")),
        kast=_percent_or_none(values.get("kast")),
        adr=_float_or_none(values.get("adr")),
        hs_pct=_percent_or_none(values.get("hsp")),
        fk=_int_or_none(values.get("fb")),
        fd=_int_or_none(values.get("fd")),
        fk_fd_diff=_int_or_none(values.get("fk-diff")),
    )


def _extract_player_stats_div(block: Tag) -> list[PlayerStat]:
    """New div-based per-map player stats. Player cells are `.ovw-cell.mod-player`;
    the rest are stat cells, evenly split per player. First half = team A
    (index 0), second half = team B (index 1)."""
    all_cells = block.select(".ovw-cell")
    if not all_cells:
        return []
    player_cells = [c for c in all_cells if "mod-player" in _cls_str(c)]
    non_player = [c for c in all_cells if "mod-player" not in _cls_str(c)]
    n = len(player_cells)
    if n < 2:
        return []
    stats_per = len(non_player) // n
    if stats_per == 0:
        return []
    half = n // 2
    stats: list[PlayerStat] = []
    for i, pcell in enumerate(player_cells):
        team_index = 0 if i < half else 1
        group = non_player[i * stats_per:(i + 1) * stats_per]
        ps = _parse_player_cell_div(pcell, group, team_index)
        if ps is not None:
            stats.append(ps)
    return stats


def _extract_player_stats(block: Tag) -> list[PlayerStat]:
    # vlr's current match pages are div-based (`.ovw-cell`); older/cached pages
    # used <table> rows. Try the new layout first, fall back to the old one.
    div_stats = _extract_player_stats_div(block)
    if div_stats:
        return div_stats
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
        candidates = soup.find_all("div", class_=re.compile(r"\bvm-stats-game\b"))
        # Keep blocks that carry stats in either the new div layout (.ovw-cell)
        # or the old table layout (<tbody>).
        blocks = [b for b in candidates if b.select(".ovw-cell") or b.find("tbody") is not None]
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

    event_id, event_name, stage_from_event = _extract_event_info(soup)

    score_a = score_b = None
    # New vlr layout uses .match-header-vs-score-winner/-loser spans; the old
    # layout used .js-spoiler spans. Both sit under .match-header-vs-score, so
    # take every span there and keep the digits in document (team) order.
    score_nodes = soup.select(".match-header-vs-score span")
    score_ints = [_int_or_none(_strip(n.get_text())) for n in score_nodes]
    score_ints = [s for s in score_ints if s is not None]
    if len(score_ints) >= 2:
        score_a, score_b = score_ints[0], score_ints[-1]

    page_text = soup.get_text(" ", strip=True)
    best_of = int(_BO_RE.search(page_text).group(1)) if _BO_RE.search(page_text) else None
    patch = _PATCH_RE.search(page_text).group(1) if _PATCH_RE.search(page_text) else None

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


# --- Player profile parser (Iteration 9 Drop 2) -----------------------------
# Extracts photo URL, country, and real name from a vlr.gg /player/{id}/ page.
# Defensive: tries multiple selectors, returns None for any field it can't find.


@dataclass
class PlayerProfile:
    player_id: int
    name: Optional[str] = None
    real_name: Optional[str] = None
    image_url: Optional[str] = None
    country: Optional[str] = None       # ISO-2 code, lowercase ('us', 'kr', 'br', etc.)
    country_name: Optional[str] = None  # human-readable, for display fallback


def parse_player_profile(html: str, player_id: int) -> PlayerProfile:
    """Parse a vlr.gg player page.

    vlr.gg's player page layout (best-effort selector targeting):
    - Header div contains an avatar image and the player's handle
    - A flag <i> tag with class like 'mod-{country_code}' near the name
    - Real name in a sibling element to the handle

    If vlr.gg changes the markup, this function still returns a PlayerProfile;
    it just leaves the unrecognised fields as None.
    """
    soup = BeautifulSoup(html, "html.parser")
    profile = PlayerProfile(player_id=player_id)

    # --- Image -------------------------------------------------------------
    # Common patterns on vlr.gg player headers
    img: Optional[Tag] = None
    for selector in [
        ".player-header img",
        ".wf-avatar img",
        "img.player-header-img",
        ".mod-player img",
    ]:
        img = soup.select_one(selector)
        if img and img.get("src"):
            break

    if img:
        src = img.get("src", "").strip()
        if src and not src.endswith("ph/sil.png"):  # vlr.gg silhouette = no photo
            # vlr.gg sometimes uses protocol-relative or path-only URLs
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://www.vlr.gg" + src
            profile.image_url = src

    # --- Country flag ------------------------------------------------------
    # Flag icons on vlr.gg have a class like 'flag mod-us'
    flag = None
    for selector in [
        ".player-header .flag",
        ".ge-text-light .flag",
        ".flag.mod-",
    ]:
        flag = soup.select_one(selector)
        if flag:
            break

    if flag:
        classes = flag.get("class") or []
        for c in classes:
            if c.startswith("mod-") and len(c) > 4:
                code = c.replace("mod-", "").strip().lower()
                # Only accept ISO-2 codes
                if len(code) == 2 and code.isalpha():
                    profile.country = code
                    break
        # Also capture the country name if present (usually next to the flag)
        # vlr.gg renders country name as sibling text
        parent = flag.parent
        if parent:
            text = parent.get_text(" ", strip=True)
            if text and len(text) < 60:
                profile.country_name = text

    # --- Handle (player name) ---------------------------------------------
    handle_el = soup.select_one(".player-header .wf-title") or soup.select_one("h1.wf-title")
    if handle_el:
        profile.name = handle_el.get_text(strip=True) or None

    # --- Real name --------------------------------------------------------
    real_el = soup.select_one(".player-header .player-real-name") or \
              soup.select_one(".wf-title-med")
    if real_el:
        text = real_el.get_text(strip=True)
        if text and text != profile.name:
            profile.real_name = text

    return profile


# --- Team logo parser ------------------------------------------------------


@dataclass
class TeamProfile:
    team_id: int
    name: Optional[str] = None
    logo_url: Optional[str] = None
    country: Optional[str] = None


def parse_team_profile(html: str, team_id: int) -> TeamProfile:
    """Parse a vlr.gg team page for the team logo and country.

    vlr.gg team page structure (best-effort):
    - Logo image in the header
    - Country flag near the team name
    """
    soup = BeautifulSoup(html, "html.parser")
    profile = TeamProfile(team_id=team_id)

    # --- Logo --------------------------------------------------------------
    logo = None
    for selector in [
        ".team-header-logo img",
        ".wf-avatar.team img",
        ".team-header img",
    ]:
        logo = soup.select_one(selector)
        if logo and logo.get("src"):
            break

    if logo:
        src = logo.get("src", "").strip()
        if src and "ph/sil" not in src:
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://www.vlr.gg" + src
            profile.logo_url = src

    # --- Country flag ------------------------------------------------------
    flag = soup.select_one(".team-header-country .flag") or \
           soup.select_one(".team-header .flag")
    if flag:
        for c in flag.get("class") or []:
            if c.startswith("mod-") and len(c) == 6:
                profile.country = c.replace("mod-", "").lower()
                break

    # --- Team name ---------------------------------------------------------
    name_el = soup.select_one(".team-header-name .wf-title") or \
              soup.select_one("h1.wf-title")
    if name_el:
        profile.name = name_el.get_text(strip=True) or None

    return profile


# --- Rankings parser (vlr.gg official team rankings) -----------------------
# https://www.vlr.gg/rankings/<region> — rank, team, vlr rating, record.


@dataclass
class RankedTeam:
    team_id: int
    name: str
    rank: Optional[int] = None
    rating: Optional[int] = None
    country: Optional[str] = None
    record: Optional[str] = None


def parse_rankings(html: str) -> list[RankedTeam]:
    """Parse a vlr.gg /rankings/<region> page into ranked teams.

    Each `.rank-item` carries the rank (`.rank-item-rank-num`), the team
    (`a.rank-item-team` → id + `data-sort-value` name + `.rank-item-team-country`),
    vlr's rating (`.rank-item-rating[data-sort-value]`), and W-L record
    (`.rank-item-record`).
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[RankedTeam] = []
    for item in soup.select(".rank-item"):
        a = item.select_one("a.rank-item-team")
        if a is None:
            continue
        m = TEAM_URL_RE.match(a.get("href", ""))
        if not m:
            continue
        team_id = int(m.group(1))

        name = a.get("data-sort-value") or ""
        if not name:
            img = a.select_one("img")
            name = (img.get("alt") if img else "") or ""
        name = _strip(name) or ""
        if not name:
            continue

        rank_el = item.select_one(".rank-item-rank-num")
        rank = _int_or_none(_strip(rank_el.get_text())) if rank_el else None

        rating = None
        rating_el = item.select_one(".rank-item-rating[data-sort-value]")
        if rating_el is not None:
            rating = _int_or_none(rating_el.get("data-sort-value"))
            if rating is None:
                rating = _int_or_none(_first_token(rating_el.get_text()))

        country_el = item.select_one(".rank-item-team-country")
        country = _strip(country_el.get_text()) if country_el else None

        record_el = item.select_one(".rank-item-record")
        record = _strip(record_el.get_text()) if record_el else None

        out.append(RankedTeam(
            team_id=team_id, name=name, rank=rank,
            rating=rating, country=country, record=record,
        ))
    return out
