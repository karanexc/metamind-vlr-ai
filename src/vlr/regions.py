"""Canonical vlr.gg rankings regions — the single source of truth.

vlr.gg/rankings exposes one page per region (``/rankings/<slug>``). We scrape
each one and store its slug directly on the team, so every regional view in the
app mirrors vlr.gg exactly instead of collapsing everything into a handful of
franchise buckets.

Order matches vlr's own region selector.
"""
from __future__ import annotations

# (slug, display label, short code) in vlr's display order.
VLR_REGIONS: list[tuple[str, str, str]] = [
    ("north-america", "North America", "NA"),
    ("europe", "Europe", "EU"),
    ("brazil", "Brazil", "BR"),
    ("asia-pacific", "Asia-Pacific", "AP"),
    ("korea", "Korea", "KR"),
    ("china", "China", "CN"),
    ("japan", "Japan", "JP"),
    ("la-s", "LA-S", "LAS"),
    ("la-n", "LA-N", "LAN"),
    ("oceania", "Oceania", "OCE"),
    ("mena", "MENA", "MN"),
    ("gc", "Game Changers", "GC"),
    ("collegiate", "Collegiate", "CG"),
]

# Slugs in scrape / display order.
VLR_REGION_SLUGS: list[str] = [slug for slug, _label, _short in VLR_REGIONS]
VLR_REGION_SET: frozenset[str] = frozenset(VLR_REGION_SLUGS)
