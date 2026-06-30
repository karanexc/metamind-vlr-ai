"""Event tier classification.

Reads event names and assigns a tier string used for opponent-strength adjustment
in feature engineering. Three tiers:

- international: VCT Masters, Champions, Kickoff, GC Championship
- tier1: regional leagues (VCT Americas/EMEA/Pacific/China Stage N)
- tier2: Challengers, VCL, Game Changers regional

Anything that doesn't match a pattern stays None, and matches from those
events count as "tier_unknown" in opponent-strength calculations.
"""
from __future__ import annotations

import re
from typing import Optional

# Tier-3 catch-all is folded into tier2 for now — sample sizes there are
# tiny and the model wouldn't learn anything reliable from a separate bucket.

_INTERNATIONAL = [
    re.compile(r"\bvalorant\s+masters\b", re.I),
    re.compile(r"\bvalorant\s+champions\b(?!\s+tour)", re.I),
    re.compile(r"\bchampions\s+tour\b.*\bmasters\b", re.I),
    re.compile(r"\bchampions\s+tour\b.*\bchampions\b", re.I),
    re.compile(r"\bvct\s+kickoff\b", re.I),
    re.compile(r"\bgame\s+changers\s+championship\b", re.I),
]

_TIER1 = [
    re.compile(r"\bvct\s+\d{4}:\s*(americas|emea|pacific|china)\b", re.I),
    re.compile(r"\bchampions\s+tour\s+\d{4}:\s*(americas|emea|pacific|china)\b", re.I),
    re.compile(r"\bvct\s+\d{4}:\s*(americas|emea|pacific|china)\s+kickoff\b", re.I),
]

_TIER2 = [
    re.compile(r"\bchallengers\s+\d{4}\b", re.I),
    re.compile(r"\bvcl\b", re.I),
    re.compile(r"\bvalorant\s+challengers\b", re.I),
    re.compile(r"\bgame\s+changers\b", re.I),
]


def classify_event_tier(name: Optional[str]) -> Optional[str]:
    r"""Return 'international', 'tier1', 'tier2', or None.

    Matches in priority order: international > tier1 > tier2. So
    "VCT 2025: Pacific Kickoff" classifies as international (Kickoff)
    rather than tier1 because the international VCT Kickoff is part of
    the international circuit even if it's branded with a region.

    Wait — actually that's wrong. Kickoff IS international, but the
    regional kickoffs (like "Pacific Kickoff") are regional events that
    just happen to be the first event of the year. Let me check the
    pattern order: _INTERNATIONAL has `vct\s+kickoff` which matches
    "VCT Kickoff" but NOT "VCT 2025: Pacific Kickoff" because the latter
    has "Pacific" between VCT and Kickoff. So this is fine — Pacific
    Kickoff matches _TIER1 (the "Pacific Kickoff" pattern).
    """
    if not name:
        return None

    for pattern in _INTERNATIONAL:
        if pattern.search(name):
            return "international"
    for pattern in _TIER1:
        if pattern.search(name):
            return "tier1"
    for pattern in _TIER2:
        if pattern.search(name):
            return "tier2"
    return None


# Numeric encoding for "avg opponent tier" features
TIER_NUMERIC = {
    "international": 3,
    "tier1": 2,
    "tier2": 1,
}


def tier_to_numeric(tier: Optional[str]) -> Optional[int]:
    return TIER_NUMERIC.get(tier) if tier else None


# --- Region classification -----------------------------------------------
# Each event belongs to a region. We use this to tag teams with their
# primary region (the one their event history most overlaps with).

_REGION_PATTERNS = [
    (re.compile(r"\b(americas|north america|brazil|latam|nrt|na |emea)?\b.*americas", re.I), "americas"),
    (re.compile(r"\bamericas\b", re.I), "americas"),
    (re.compile(r"\b(brazil|latam|north america|na\b)", re.I), "americas"),

    (re.compile(r"\bemea\b", re.I), "emea"),
    (re.compile(r"\b(europe|mena|middle east|africa|turkey)\b", re.I), "emea"),

    (re.compile(r"\bpacific\b", re.I), "pacific"),
    (re.compile(r"\b(korea|japan|sea|south east asia|oceania|south asia)\b", re.I), "pacific"),

    (re.compile(r"\bchina\b", re.I), "china"),
]


def classify_event_region(name: Optional[str]) -> Optional[str]:
    """Return 'americas', 'emea', 'pacific', 'china', or None for international/unknown."""
    if not name:
        return None
    # International events (Masters, Champions, Kickoff) don't have a region
    if re.search(r"\b(masters|champions|kickoff)\b", name, re.I) and not re.search(
        r"\b(americas|emea|pacific|china)\b", name, re.I
    ):
        return None
    for pattern, region in _REGION_PATTERNS:
        if pattern.search(name):
            return region
    return None


REGION_DISPLAY = {
    "americas": "Americas",
    "emea": "EMEA",
    "pacific": "Pacific",
    "china": "China",
}
