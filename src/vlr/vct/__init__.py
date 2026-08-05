"""VCT esports telemetry module.

A self-contained, historical add-on to the live vlr pipeline. It imports Riot's
publicly-released VCT esports game data (the "VCT Hackathon" S3 dataset,
2022-2024) and derives per-player / per-agent ABILITY and ULTIMATE usage —
data vlr.gg does not expose. It links to the live players by handle.

Kept deliberately decoupled: nothing here runs on the 2-hour scheduler; it's a
one-time (re-runnable) import via `python -m src.vlr.cli import-vct-abilities`.
"""
