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
