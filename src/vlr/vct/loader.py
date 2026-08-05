"""Import VCT games into Postgres: download -> parse -> aggregate -> upsert.

Idempotent: games already in `vct_games` are skipped, so it's safe to re-run
and to stop/resume. Not wired into the scheduler — run on demand via the CLI.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from ..db.models import VctAbilityStat, VctGame, VctRound
from ..db.session import get_session
from . import download
from .parse import parse_game

log = logging.getLogger(__name__)


def _team_tag(handles: list[str]) -> Optional[str]:
    """Most common leading token among handles, e.g. 'SMG Yoky' -> 'SMG'."""
    tags = [h.split(" ", 1)[0] for h in handles if h and " " in h]
    if not tags:
        return None
    return Counter(tags).most_common(1)[0][0]


def _player_name(handle: str, tag: Optional[str]) -> str:
    """Strip the team tag so the name links to the live vlr player list."""
    if tag and handle.startswith(tag + " "):
        return handle[len(tag) + 1:].strip()
    return handle.strip()


def _parse_dt(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None


def import_vct_games(tier: str, year: int, limit: Optional[int] = None,
                     delay: float = 0.0, on_progress=None) -> dict:
    """Import a subset of VCT games for (tier, year). Returns a stats dict."""
    stats = {"scanned": 0, "imported": 0, "skipped": 0, "failed": 0, "players": 0}
    keys = download.list_game_keys(tier, year, limit)
    amap = download.agent_map()
    mmap = download.map_map()

    session = get_session()
    try:
        existing = set(session.execute(select(VctGame.game_id)).scalars().all())
        total = len(keys)
        for i, key in enumerate(keys):
            stats["scanned"] += 1
            gid = key.rsplit("/", 1)[-1].replace(".json.gz", "")
            if gid in existing:
                stats["skipped"] += 1
                if on_progress:
                    on_progress(i, total, gid, "skip")
                continue
            try:
                result = parse_game(download.fetch_game(key), amap, mmap)
                if result is None or not result.players:
                    stats["failed"] += 1
                    if on_progress:
                        on_progress(i, total, gid, "empty")
                    continue

                by_team: dict = {}
                for p in result.players:
                    by_team.setdefault(p.team_id, []).append(p.handle)
                team_tags = {tid: _team_tag(hs) for tid, hs in by_team.items()}
                tids = list(result.team_names.keys())

                game = VctGame(
                    game_id=result.game_id or gid, tier=tier, year=year,
                    map_name=result.map_name, played_at=_parse_dt(result.date),
                    total_rounds=result.total_rounds,
                    team_a_tag=team_tags.get(tids[0]) if len(tids) > 0 else None,
                    team_b_tag=team_tags.get(tids[1]) if len(tids) > 1 else None,
                    winner_tag=team_tags.get(result.winner_team_id),
                )
                session.add(game)
                for p in result.players:
                    tag = team_tags.get(p.team_id)
                    session.add(VctAbilityStat(
                        game_id=game.game_id, handle=p.handle,
                        player_name=_player_name(p.handle, tag), team_tag=tag,
                        agent=p.agent, role=p.role, rounds=result.total_rounds,
                        ability_casts=p.ability1_casts + p.ability2_casts + p.grenade_casts,
                        ult_casts=p.ult_casts, kills=p.kills, deaths=p.deaths, won=p.won,
                    ))
                    stats["players"] += 1

                # per-round records (outcome + utility + timeline)
                for r in result.rounds:
                    wid = r.get("winner_team_id")
                    lid = next((t for t in tids if t != wid), None)
                    rnum = r.get("round_number")
                    session.add(VctRound(
                        game_id=game.game_id, round_number=rnum,
                        winner_tag=team_tags.get(wid),
                        win_condition=r.get("win_condition"),
                        attacker_tag=team_tags.get(r.get("attacker_team_id")),
                        winner_util=r["util"].get(wid, 0), loser_util=r["util"].get(lid, 0),
                        winner_ults=r["ults"].get(wid, 0), loser_ults=r["ults"].get(lid, 0),
                        opening_kill_tag=team_tags.get(r.get("opening_kill_team_id")),
                        spike_planted=bool(r.get("spike_planted")),
                        spike_defused=bool(r.get("spike_defused")),
                        is_pistol=rnum in (1, 13),
                        is_map_point=rnum == result.total_rounds,
                        is_clutch=bool(r.get("reached_1v2", {}).get(wid)),
                        timeline=r.get("timeline"),
                    ))
                session.commit()
                existing.add(game.game_id)
                stats["imported"] += 1
                if on_progress:
                    on_progress(i, total, gid, "ok")
            except Exception:
                session.rollback()
                log.exception("VCT import failed for %s", gid)
                stats["failed"] += 1
                if on_progress:
                    on_progress(i, total, gid, "error")
            if delay:
                time.sleep(delay)
        return stats
    finally:
        session.close()
