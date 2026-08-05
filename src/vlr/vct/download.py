"""Fetch helpers for the public VCT esports dataset + valorant-api art refs.

The dataset lives in a public S3 bucket (no credentials needed):
    https://vcthackathon-data.s3.amazonaws.com/
    <tier>/games/<year>/<platformGameId>.json.gz    (gzipped event stream)

Agent/map GUIDs resolve via the free valorant-api.com community API.
Everything here is stdlib-only (urllib + gzip) — no boto3, no new deps.
"""
from __future__ import annotations

import gzip
import json
import re
import urllib.parse
import urllib.request
from typing import Optional

S3_BASE = "https://vcthackathon-data.s3.amazonaws.com/"
_UA = {"User-Agent": "Mozilla/5.0 (vlr-analytics VCT importer)"}
TIERS = ("game-changers", "vct-challengers", "vct-international")


def _get(url: str, timeout: int = 120) -> bytes:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=_UA), timeout=timeout
    ).read()


def list_game_keys(tier: str, year: int, limit: Optional[int] = None) -> list[str]:
    """S3 keys for game files under <tier>/games/<year>/ (handles pagination)."""
    prefix = f"{tier}/games/{year}/"
    keys: list[str] = []
    token: Optional[str] = None
    while True:
        url = S3_BASE + f"?list-type=2&prefix={urllib.parse.quote(prefix)}&max-keys=1000"
        if token:
            url += f"&continuation-token={urllib.parse.quote(token)}"
        xml = _get(url).decode("utf-8", "replace")
        keys.extend(re.findall(r"<Key>([^<]+\.json\.gz)</Key>", xml))
        if limit and len(keys) >= limit:
            return keys[:limit]
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
        if not m:
            break
        token = m.group(1)
    return keys[:limit] if limit else keys


def fetch_game(key: str) -> list:
    """Download + decompress one game file into its list of events."""
    raw = _get(S3_BASE + urllib.parse.quote(key, safe="/"))
    return json.loads(gzip.decompress(raw).decode("utf-8", "replace"))


_agent_map: Optional[dict] = None
_map_map: Optional[dict] = None


def agent_map() -> dict:
    """{AGENT_GUID_UPPER: (name, role)} from valorant-api (cached, fails soft)."""
    global _agent_map
    if _agent_map is None:
        try:
            data = json.loads(_get(
                "https://valorant-api.com/v1/agents?isPlayableCharacter=true", 60
            ).decode("utf-8", "replace"))
            _agent_map = {
                a["uuid"].upper(): (a["displayName"], (a.get("role") or {}).get("displayName"))
                for a in data.get("data", [])
            }
        except Exception:
            _agent_map = {}
    return _agent_map


def map_map() -> dict:
    """{map_asset_path: display_name} from valorant-api (cached, fails soft)."""
    global _map_map
    if _map_map is None:
        try:
            data = json.loads(_get("https://valorant-api.com/v1/maps", 60).decode("utf-8", "replace"))
            _map_map = {m["mapUrl"]: m["displayName"] for m in data.get("data", []) if m.get("mapUrl")}
        except Exception:
            _map_map = {}
    return _map_map
