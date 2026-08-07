"""VCT ability telemetry endpoints — the historical (2022-24) ability module.

Serves derived ability + ultimate usage aggregated from Riot's VCT dataset.
All data is clearly historical and separate from the live vlr scrape.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import Integer, cast, func, nullslast, select

from vlr.db.models import VctAbilityStat, VctGame, VctRound
from vlr.db.session import get_session

router = APIRouter()


def _rate(n, d):
    return round(n / d, 2) if d else 0.0


@router.get("/abilities/summary")
async def abilities_summary() -> dict:
    """Coverage of the imported VCT ability corpus."""
    session = get_session()
    try:
        games = session.execute(select(func.count(VctGame.game_id))).scalar() or 0
        players = session.execute(
            select(func.count(func.distinct(VctAbilityStat.player_name)))
        ).scalar() or 0
        agents = session.execute(
            select(func.count(func.distinct(VctAbilityStat.agent)))
            .where(VctAbilityStat.agent.isnot(None))
        ).scalar() or 0
        yr = session.execute(select(func.min(VctGame.year), func.max(VctGame.year))).one()
        tiers = session.execute(select(func.distinct(VctGame.tier))).scalars().all()
        return {
            "games": int(games), "players": int(players), "agents": int(agents),
            "year_min": yr[0], "year_max": yr[1], "tiers": list(tiers),
        }
    finally:
        session.close()


@router.get("/abilities/agents")
async def abilities_agents(
    min_games: int = Query(5, ge=1, le=1000),
    map: str = Query("", max_length=32),
) -> list[dict]:
    """Per-agent ability/ult usage, ordered by ability activity per round.

    Optional `map` filter restricts to games on that map (map-wise view).
    """
    session = get_session()
    try:
        q = select(
            VctAbilityStat.agent,
            func.max(VctAbilityStat.role),
            func.count().label("n"),
            func.coalesce(func.sum(VctAbilityStat.rounds), 0),
            func.coalesce(func.sum(VctAbilityStat.ability_casts), 0),
            func.coalesce(func.sum(VctAbilityStat.ult_casts), 0),
            func.coalesce(func.sum(VctAbilityStat.kills), 0),
            func.coalesce(func.sum(VctAbilityStat.deaths), 0),
            func.coalesce(func.sum(cast(VctAbilityStat.won, Integer)), 0),
        ).where(VctAbilityStat.agent.isnot(None))
        if map.strip():
            q = q.join(VctGame, VctGame.game_id == VctAbilityStat.game_id).where(
                VctGame.map_name == map.strip()
            )
        q = q.group_by(VctAbilityStat.agent).having(func.count() >= min_games)
        rows = session.execute(q).all()

        out = []
        for agent, role, n, rounds, ab, ult, k, d, wins in rows:
            out.append({
                "agent": agent, "role": role, "games": int(n),
                "ability_casts_per_round": _rate(ab, rounds),
                "ults_per_game": _rate(ult, n),
                "ult_per_round": _rate(ult, rounds),
                "kd": _rate(k, d),
                "win_rate": round(100.0 * wins / n, 1) if n else 0.0,
            })
        out.sort(key=lambda r: r["ability_casts_per_round"], reverse=True)
        return out
    finally:
        session.close()


def _player_rows(session, where=None, limit=None):
    q = (
        select(
            VctAbilityStat.player_name,
            func.count().label("n"),
            func.coalesce(func.sum(VctAbilityStat.rounds), 0),
            func.coalesce(func.sum(VctAbilityStat.ability_casts), 0),
            func.coalesce(func.sum(VctAbilityStat.ult_casts), 0),
            func.coalesce(func.sum(VctAbilityStat.kills), 0),
            func.coalesce(func.sum(VctAbilityStat.deaths), 0),
            func.coalesce(func.sum(cast(VctAbilityStat.won, Integer)), 0),
            func.max(VctAbilityStat.team_tag),
        )
        .group_by(VctAbilityStat.player_name)
    )
    if where is not None:
        q = q.where(where)
    if limit:
        q = q.order_by(func.count().desc()).limit(limit)
    return session.execute(q).all()


def _shape_player(row) -> dict:
    name, n, rounds, ab, ult, k, d, wins, tag = row
    return {
        "player_name": name, "team_tag": tag, "games": int(n),
        "ability_casts_per_round": _rate(ab, rounds),
        "ults_per_game": _rate(ult, n),
        "kd": _rate(k, d),
        "win_rate": round(100.0 * wins / n, 1) if n else 0.0,
    }


@router.get("/abilities/players")
async def abilities_players(
    search: str = Query("", max_length=64),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Player ability profiles (searchable). Links to live players by name."""
    session = get_session()
    try:
        where = None
        if search.strip():
            where = VctAbilityStat.player_name.ilike(f"%{search.strip()}%")
        rows = _player_rows(session, where=where, limit=limit)
        return [_shape_player(r) for r in rows]
    finally:
        session.close()


@router.get("/abilities/players/{name}")
async def abilities_player(name: str) -> dict:
    """One player's ability profile + per-agent breakdown. 404-safe (empty)."""
    session = get_session()
    try:
        rows = _player_rows(session, where=VctAbilityStat.player_name.ilike(name))
        if not rows:
            return {"found": False, "player_name": name}
        profile = _shape_player(rows[0])
        agents = session.execute(
            select(
                VctAbilityStat.agent,
                func.count(),
                func.coalesce(func.sum(VctAbilityStat.ult_casts), 0),
            )
            .where(VctAbilityStat.player_name.ilike(name))
            .where(VctAbilityStat.agent.isnot(None))
            .group_by(VctAbilityStat.agent)
            .order_by(func.count().desc())
        ).all()
        profile["found"] = True
        profile["agents"] = [
            {"agent": a, "games": int(c), "ults": int(u)} for a, c, u in agents
        ]
        return profile
    finally:
        session.close()


# --- Impact analysis (round-level) ---------------------------------------

_DIFF_ORDER = ["≤ -6", "-5..-3", "-2..-1", "0", "1..2", "3..5", "≥ 6"]


def _diff_bucket(d: int) -> str:
    if d <= -6:
        return "≤ -6"
    if d <= -3:
        return "-5..-3"
    if d <= -1:
        return "-2..-1"
    if d == 0:
        return "0"
    if d <= 2:
        return "1..2"
    if d <= 5:
        return "3..5"
    return "≥ 6"


@router.get("/abilities/impact")
async def abilities_impact(map: str = Query("", max_length=32)) -> dict:
    """Does utility win rounds? Headline rates + win-rate curves + by-condition.

    Each round is expanded into two team-observations (the winner and the
    loser) so win-rate-by-utility is measured symmetrically, not winner-biased.
    """
    session = get_session()
    try:
        q = select(
            VctRound.winner_util, VctRound.loser_util,
            VctRound.winner_ults, VctRound.loser_ults,
            VctRound.win_condition,
            VctRound.opening_kill_tag, VctRound.winner_tag,
        )
        if map.strip():
            q = q.join(VctGame, VctGame.game_id == VctRound.game_id).where(
                VctGame.map_name == map.strip()
            )
        rows = session.execute(q).all()
        n = len(rows)

        edge_won = edge_total = ult_won = ult_total = fb_won = fb_total = 0
        diff_bins: dict = {b: [0, 0] for b in _DIFF_ORDER}   # bucket -> [wins, obs]
        ult_bins: dict = {"0": [0, 0], "1": [0, 0], "2": [0, 0], "3+": [0, 0]}
        cond: dict = {}

        def _ub(u):
            return "3+" if u >= 3 else str(u)

        for wu, lu, wx, lx, wc, okt, wt in rows:
            wu, lu, wx, lx = wu or 0, lu or 0, wx or 0, lx or 0
            if okt is not None and wt is not None:
                fb_total += 1
                if okt == wt:
                    fb_won += 1
            # utility edge
            if wu != lu:
                edge_total += 1
                if wu > lu:
                    edge_won += 1
            # one-sided ult
            if (wx > 0) != (lx > 0):
                ult_total += 1
                if wx > 0:
                    ult_won += 1
            # two team-observations for the curves
            diff_bins[_diff_bucket(wu - lu)][0] += 1
            diff_bins[_diff_bucket(wu - lu)][1] += 1
            diff_bins[_diff_bucket(lu - wu)][1] += 1
            ult_bins[_ub(wx)][0] += 1
            ult_bins[_ub(wx)][1] += 1
            ult_bins[_ub(lx)][1] += 1
            # by win condition
            c = cond.setdefault(wc or "OTHER", [0, 0, 0])
            c[0] += 1
            c[1] += wu
            c[2] += wx

        return {
            "rounds": n,
            "utility_edge_win_rate": round(100.0 * edge_won / edge_total, 1) if edge_total else 0.0,
            "ult_win_rate": round(100.0 * ult_won / ult_total, 1) if ult_total else 0.0,
            "first_blood_win_rate": round(100.0 * fb_won / fb_total, 1) if fb_total else 0.0,
            "util_diff_buckets": [
                {"bucket": b, "n": diff_bins[b][1],
                 "win_rate": round(100.0 * diff_bins[b][0] / diff_bins[b][1], 1) if diff_bins[b][1] else 0.0}
                for b in _DIFF_ORDER
            ],
            "ult_buckets": [
                {"ults": k, "n": v[1],
                 "win_rate": round(100.0 * v[0] / v[1], 1) if v[1] else 0.0}
                for k, v in ult_bins.items()
            ],
            "by_condition": [
                {"condition": k, "rounds": v[0],
                 "avg_util": round(v[1] / v[0], 1) if v[0] else 0.0,
                 "avg_ults": round(v[2] / v[0], 2) if v[0] else 0.0}
                for k, v in sorted(cond.items(), key=lambda kv: -kv[1][0])
            ],
        }
    finally:
        session.close()


@router.get("/abilities/impact/maps")
async def abilities_impact_maps() -> list[dict]:
    """Per-map impact: utility-edge win rate, ult win rate, sample size."""
    session = get_session()
    try:
        rows = session.execute(
            select(
                VctGame.map_name, VctRound.game_id,
                VctRound.winner_util, VctRound.loser_util,
                VctRound.winner_ults, VctRound.loser_ults,
            )
            .join(VctGame, VctGame.game_id == VctRound.game_id)
            .where(VctGame.map_name.isnot(None))
        ).all()

        agg: dict = {}
        for mp, gid, wu, lu, wx, lx in rows:
            a = agg.setdefault(mp, {"games": set(), "rounds": 0,
                                    "edge_won": 0, "edge_total": 0,
                                    "ult_won": 0, "ult_total": 0, "util": 0})
            a["games"].add(gid)
            a["rounds"] += 1
            a["util"] += (wu or 0)
            if (wu or 0) != (lu or 0):
                a["edge_total"] += 1
                if (wu or 0) > (lu or 0):
                    a["edge_won"] += 1
            if ((wx or 0) > 0) != ((lx or 0) > 0):
                a["ult_total"] += 1
                if (wx or 0) > 0:
                    a["ult_won"] += 1

        out = []
        for mp, a in agg.items():
            out.append({
                "map": mp, "games": len(a["games"]), "rounds": a["rounds"],
                "utility_edge_win_rate": round(100.0 * a["edge_won"] / a["edge_total"], 1) if a["edge_total"] else 0.0,
                "ult_win_rate": round(100.0 * a["ult_won"] / a["ult_total"], 1) if a["ult_total"] else 0.0,
                "avg_util_per_round": round(a["util"] / a["rounds"], 1) if a["rounds"] else 0.0,
            })
        out.sort(key=lambda r: r["rounds"], reverse=True)
        return out
    finally:
        session.close()


@router.get("/abilities/impact/breakdown")
async def abilities_impact_breakdown() -> dict:
    """The high-signal impact views: opening-duel conversion per agent, ult
    conversion per agent, and role-composition win rates."""
    from collections import Counter
    session = get_session()
    try:
        # Opening-duel: win rate of the round when this agent gets first blood.
        fb: dict = {}
        for oka, okt, wt in session.execute(
            select(VctRound.opening_kill_agent, VctRound.opening_kill_tag, VctRound.winner_tag)
            .where(VctRound.opening_kill_agent.isnot(None))
        ).all():
            a = fb.setdefault(oka, [0, 0])
            a[1] += 1
            if okt is not None and okt == wt:
                a[0] += 1
        first_blood = sorted(
            [{"agent": k, "first_bloods": v[1], "win_pct": round(100 * v[0] / v[1], 1)}
             for k, v in fb.items() if v[1] >= 10],
            key=lambda r: -r["first_bloods"],
        )

        # Ult conversion: round win rate when this agent uses their ultimate.
        uc: dict = {}
        for (ults,) in session.execute(
            select(VctRound.ult_agents).where(VctRound.ult_agents.isnot(None))
        ).all():
            for u in (ults or []):
                ag = u.get("agent")
                if not ag:
                    continue
                a = uc.setdefault(ag, [0, 0])
                a[1] += 1
                if u.get("won"):
                    a[0] += 1
        ult_conversion = sorted(
            [{"agent": k, "ult_rounds": v[1], "win_pct": round(100 * v[0] / v[1], 1)}
             for k, v in uc.items() if v[1] >= 10],
            key=lambda r: -r["win_pct"],
        )

        # Role composition win rate (from the per-game team rosters).
        gt: dict = {}
        for gid, tag, role, won in session.execute(
            select(VctAbilityStat.game_id, VctAbilityStat.team_tag,
                   VctAbilityStat.role, VctAbilityStat.won)
            .where(VctAbilityStat.role.isnot(None))
        ).all():
            d = gt.setdefault((gid, tag), {"roles": Counter(), "won": False})
            d["roles"][role] += 1
            d["won"] = d["won"] or bool(won)
        rc: dict = {}
        for d in gt.values():
            sig = tuple(sorted(d["roles"].items()))
            a = rc.setdefault(sig, [0, 0])
            a[1] += 1
            if d["won"]:
                a[0] += 1
        role_comps = sorted(
            [{"label": " / ".join(f"{c} {r}" for r, c in sig), "games": v[1],
              "win_pct": round(100 * v[0] / v[1], 1)}
             for sig, v in rc.items() if v[1] >= 10],
            key=lambda r: -r["win_pct"],
        )

        return {"first_blood": first_blood, "ult_conversion": ult_conversion, "role_comps": role_comps}
    finally:
        session.close()


@router.get("/abilities/games")
async def abilities_games(
    map: str = Query("", max_length=32),
    search: str = Query("", max_length=64),
    limit: int = Query(60, ge=1, le=200),
) -> list[dict]:
    """List imported games (for the round-timeline selector), newest first."""
    session = get_session()
    try:
        q = select(VctGame)
        if map.strip():
            q = q.where(VctGame.map_name == map.strip())
        if search.strip():
            s = f"%{search.strip()}%"
            q = q.where((VctGame.team_a_tag.ilike(s)) | (VctGame.team_b_tag.ilike(s)))
        q = q.order_by(nullslast(VctGame.played_at.desc())).limit(limit)
        games = session.execute(q).scalars().all()

        gids = [g.game_id for g in games]
        score: dict = {}
        if gids:
            for gid, tag, c in session.execute(
                select(VctRound.game_id, VctRound.winner_tag, func.count())
                .where(VctRound.game_id.in_(gids))
                .group_by(VctRound.game_id, VctRound.winner_tag)
            ).all():
                score.setdefault(gid, {})[tag] = int(c)

        out = []
        for g in games:
            s = score.get(g.game_id, {})
            out.append({
                "game_id": g.game_id, "map": g.map_name,
                "tier": g.tier, "year": g.year,
                "team_a_tag": g.team_a_tag, "team_b_tag": g.team_b_tag,
                "winner_tag": g.winner_tag,
                "score_a": s.get(g.team_a_tag, 0), "score_b": s.get(g.team_b_tag, 0),
                "played_at": g.played_at.isoformat() if g.played_at else None,
                "total_rounds": g.total_rounds,
            })
        return out
    finally:
        session.close()


@router.get("/abilities/games/{game_id}/rounds")
async def abilities_game_rounds(game_id: str) -> dict:
    """Full match breakdown: scoreboard (team/player/agent), impact highlights,
    per-round outcomes + timelines."""
    session = get_session()
    try:
        g = session.get(VctGame, game_id)
        if g is None:
            return {"found": False, "game_id": game_id}
        rounds = session.execute(
            select(VctRound).where(VctRound.game_id == game_id)
            .order_by(VctRound.round_number)
        ).scalars().all()

        pstats = session.execute(
            select(VctAbilityStat).where(VctAbilityStat.game_id == game_id)
        ).scalars().all()
        players = [
            {
                "handle": p.handle, "player_name": p.player_name, "team_tag": p.team_tag,
                "agent": p.agent, "role": p.role, "ability_casts": p.ability_casts,
                "ult_casts": p.ult_casts, "kills": p.kills, "deaths": p.deaths, "won": p.won,
            }
            for p in pstats
        ]
        # team totals
        teams: dict = {}
        for p in pstats:
            t = teams.setdefault(p.team_tag, {"team_tag": p.team_tag, "util": 0, "ults": 0, "kills": 0, "won": False})
            t["util"] += p.ability_casts or 0
            t["ults"] += p.ult_casts or 0
            t["kills"] += p.kills or 0
            t["won"] = t["won"] or bool(p.won)

        # impact highlights
        def _top(attr):
            best = max(pstats, key=lambda p: getattr(p, attr) or 0, default=None)
            if best is None or (getattr(best, attr) or 0) <= 0:
                return None
            return {"player_name": best.player_name, "agent": best.agent, "value": getattr(best, attr)}

        edge_rounds = sum(1 for r in rounds if (r.winner_util or 0) > (r.loser_util or 0))
        decisive = next((r.round_number for r in rounds if r.is_map_point), None)
        if decisive is None:
            decisive = next((r.round_number for r in rounds if r.is_clutch), None)
        highlights = {
            "most_utility": _top("ability_casts"),
            "most_ults": _top("ult_casts"),
            "top_fragger": _top("kills"),
            "utility_edge_rounds": edge_rounds,
            "total_rounds": len(rounds),
            "decisive_round": decisive,
        }

        return {
            "found": True,
            "game": {
                "game_id": g.game_id, "map": g.map_name, "tier": g.tier, "year": g.year,
                "team_a_tag": g.team_a_tag, "team_b_tag": g.team_b_tag,
                "winner_tag": g.winner_tag, "total_rounds": g.total_rounds,
                "played_at": g.played_at.isoformat() if g.played_at else None,
            },
            "players": players,
            "teams": list(teams.values()),
            "highlights": highlights,
            "rounds": [
                {
                    "round_number": r.round_number, "winner_tag": r.winner_tag,
                    "win_condition": r.win_condition, "attacker_tag": r.attacker_tag,
                    "winner_util": r.winner_util, "loser_util": r.loser_util,
                    "winner_ults": r.winner_ults, "loser_ults": r.loser_ults,
                    "opening_kill_tag": r.opening_kill_tag,
                    "spike_planted": r.spike_planted, "spike_defused": r.spike_defused,
                    "is_pistol": r.is_pistol, "is_map_point": r.is_map_point,
                    "is_clutch": r.is_clutch, "timeline": r.timeline or [],
                }
                for r in rounds
            ],
        }
    finally:
        session.close()
