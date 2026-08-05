"""Team endpoints: list + detail."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from vlr.app import data
from vlr.api.schemas import TeamListItem, TeamSummary
from vlr.regions import VLR_REGION_SET

router = APIRouter()


@router.get("/teams", response_model=list[TeamListItem])
async def list_teams(min_matches: int = Query(5, ge=1, le=100)) -> list[TeamListItem]:
    """List all teams that have played at least `min_matches` matches."""
    opts = data.get_team_options(min_matches=min_matches)
    # Attach logos in one extra query, without changing the shared
    # get_team_options() signature (used by the Streamlit app + pickem).
    logos: dict[int, str] = {}
    ids = [tid for tid, _, _ in opts]
    if ids:
        from vlr.db.session import get_session
        from vlr.db.models import Team
        from sqlalchemy import select as _select
        session = get_session()
        try:
            for tid, logo in session.execute(
                _select(Team.id, Team.logo_url).where(Team.id.in_(ids))
            ).all():
                if logo:
                    logos[int(tid)] = logo
        finally:
            session.close()
    return [
        TeamListItem(id=tid, name=name, n_matches=n, logo_url=logos.get(tid))
        for tid, name, n in opts
    ]


@router.get("/teams/{team_id}", response_model=TeamSummary)
async def get_team(team_id: int) -> TeamSummary:
    summary = data.get_team_summary(team_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found")

    # Convert dataframes to dict-list format for JSON
    return TeamSummary(
        id=team_id,
        name=summary["name"],
        n_matches=summary["n_matches"],
        n_wins=summary["n_wins"],
        match_win_rate=summary["match_win_rate"],
        map_wins=summary["map_wins"],
        map_total=summary["map_total"],
        map_win_rate=summary["map_win_rate"],
        roster=[{"id": pid, "name": name} for pid, name in summary["roster"]],
        recent_matches=[
            {
                "match_id": int(r["match_id"]),
                "team_a": r["team_a"],
                "team_b": r["team_b"],
                "score_a": int(r["score_a"]),
                "score_b": int(r["score_b"]),
                "datetime": r["datetime"].isoformat() if r["datetime"] is not None else None,
                "event": r["event"],
                "best_of": int(r["best_of"]) if r["best_of"] is not None else None,
            }
            for _, r in summary["recent_matches"].iterrows()
        ],
        per_map=[
            {
                "map": r["map"], "played": int(r["played"]),
                "wins": int(r["wins"]), "win_rate": float(r["win_rate"]),
            }
            for _, r in summary["per_map"].iterrows()
        ] if not summary["per_map"].empty else [],
    )


def _wl_from_record(record) -> tuple[int, int]:
    """Parse a vlr record string like '70–44' into (wins, losses)."""
    import re
    if not record:
        return 0, 0
    nums = re.findall(r"\d+", str(record))
    wins = int(nums[0]) if len(nums) >= 1 else 0
    losses = int(nums[1]) if len(nums) >= 2 else 0
    return wins, losses


@router.get("/regions/{region}/top-teams")
async def regional_top_teams(
    region: str,
    limit: int = Query(5, ge=1, le=20),
) -> list[dict]:
    """Top teams in a vlr.gg region by official vlr.gg rating."""
    if region not in VLR_REGION_SET:
        raise HTTPException(status_code=400, detail=f"unknown region '{region}'")

    from vlr.db.session import get_session
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        rows = session.execute(sql_text("""
            SELECT t.id, t.name, t.logo_url, t.country,
                   t.vlr_rating, t.vlr_rank, t.vlr_record
            FROM teams t
            WHERE t.vlr_rating IS NOT NULL AND t.region = :region
            ORDER BY t.vlr_rating DESC NULLS LAST, t.vlr_rank ASC NULLS LAST
            LIMIT :limit
        """), {"region": region, "limit": limit}).all()

        out = []
        for r in rows:
            wins, losses = _wl_from_record(r[6])
            played = wins + losses
            out.append({
                "id": int(r[0]),
                "name": r[1],
                "logo_url": r[2],
                "country": r[3],
                "vlr_rating": int(r[4]) if r[4] is not None else None,
                "vlr_rank": int(r[5]) if r[5] is not None else None,
                "matches_played": played,
                "wins": wins,
                "losses": losses,
                "win_pct": round(100.0 * wins / played, 1) if played else 0.0,
            })
        return out
    finally:
        session.close()


@router.get("/teams/{team_id}/roster")
async def team_roster(team_id: int) -> list[dict]:
    """Current roster — the 5 players who most recently played for this team."""
    from vlr.db.session import get_session
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        rows = session.execute(sql_text("""
            WITH recent AS (
                SELECT pms.player_id,
                       MAX(m.match_datetime) AS last_played
                FROM player_map_stats pms
                JOIN matches m ON m.id = pms.match_id
                WHERE pms.team_id = :tid
                  AND m.match_datetime IS NOT NULL
                GROUP BY pms.player_id
                ORDER BY MAX(m.match_datetime) DESC
                LIMIT 5
            )
            SELECT p.id, p.name, p.image_url, p.country, p.real_name,
                   r.last_played
            FROM recent r
            JOIN players p ON p.id = r.player_id
            ORDER BY r.last_played DESC
        """), {"tid": team_id}).all()

        return [
            {
                "id": int(r[0]),
                "name": r[1],
                "image_url": r[2],
                "country": r[3],
                "real_name": r[4],
                "last_played": r[5].isoformat() if r[5] is not None else None,
            }
            for r in rows
        ]
    finally:
        session.close()


@router.get("/regions/{region}/teams-leaderboard")
async def regional_teams_leaderboard(
    region: str,
    limit: int = Query(50, ge=5, le=100),
) -> list[dict]:
    """Region leaderboard ranked by official vlr.gg rating, with inline roster.

    Powers the Teams page. Only teams that appear in vlr's rankings are shown,
    ordered by vlr rating (highest first).
    """
    if region != "all" and region not in VLR_REGION_SET:
        raise HTTPException(status_code=400, detail=f"unknown region '{region}'")

    from vlr.db.session import get_session
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        region_filter = "" if region == "all" else "AND t.region = :region"
        params = {"limit": limit}
        if region != "all":
            params["region"] = region

        team_rows = session.execute(sql_text(f"""
            SELECT t.id, t.name, t.region, t.logo_url, t.country,
                   t.vlr_rating, t.vlr_rank, t.vlr_record
            FROM teams t
            WHERE t.vlr_rating IS NOT NULL {region_filter}
            ORDER BY t.vlr_rating DESC NULLS LAST, t.vlr_rank ASC NULLS LAST
            LIMIT :limit
        """), params).all()

        if not team_rows:
            return []

        team_ids = [int(r[0]) for r in team_rows]

        # Fetch rosters in one query for all teams (top-5 most recent players each)
        roster_rows = session.execute(sql_text("""
            WITH ranked AS (
                SELECT pms.team_id, p.id AS player_id, p.name, p.image_url, p.country,
                       MAX(m.match_datetime) AS last_played,
                       ROW_NUMBER() OVER (
                           PARTITION BY pms.team_id
                           ORDER BY MAX(m.match_datetime) DESC
                       ) AS rn
                FROM player_map_stats pms
                JOIN players p ON p.id = pms.player_id
                JOIN matches m ON m.id = pms.match_id
                WHERE pms.team_id = ANY(:tids) AND m.match_datetime IS NOT NULL
                GROUP BY pms.team_id, p.id, p.name, p.image_url, p.country
            )
            SELECT team_id, player_id, name, image_url, country
            FROM ranked
            WHERE rn <= 5
            ORDER BY team_id, rn
        """), {"tids": team_ids}).all()

        rosters: dict[int, list[dict]] = {}
        for tid, pid, name, img, country in roster_rows:
            rosters.setdefault(int(tid), []).append({
                "id": int(pid), "name": name,
                "image_url": img, "country": country,
            })

        out = []
        for r in team_rows:
            wins, losses = _wl_from_record(r[7])
            played = wins + losses
            out.append({
                "id": int(r[0]),
                "name": r[1],
                "region": r[2],
                "logo_url": r[3],
                "country": r[4],
                "vlr_rating": int(r[5]) if r[5] is not None else None,
                "vlr_rank": int(r[6]) if r[6] is not None else None,
                "matches_played": played,
                "wins": wins,
                "losses": losses,
                "win_pct": round(100.0 * wins / played, 1) if played else 0.0,
                "roster": rosters.get(int(r[0]), []),
            })
        return out
    finally:
        session.close()
