"""Team endpoints: list + detail."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from vlr.app import data
from vlr.api.schemas import TeamListItem, TeamSummary

router = APIRouter()


@router.get("/teams", response_model=list[TeamListItem])
async def list_teams(min_matches: int = Query(5, ge=1, le=100)) -> list[TeamListItem]:
    """List all teams that have played at least `min_matches` matches."""
    return [
        TeamListItem(id=tid, name=name, n_matches=n)
        for tid, name, n in data.get_team_options(min_matches=min_matches)
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


@router.get("/regions/{region}/top-teams")
async def regional_top_teams(
    region: str,
    limit: int = Query(5, ge=1, le=20),
    days: int = Query(120, ge=30, le=365),
    min_matches: int = Query(10, ge=1, le=50),
) -> list[dict]:
    """Top teams in a region by match win rate over the last `days` days.

    Only includes teams with at least `min_matches` decided matches in that
    window — filters out small samples where a 2-0 record looks dominant.
    """
    if region not in {"americas", "emea", "pacific", "china"}:
        raise HTTPException(
            status_code=400,
            detail="region must be 'americas', 'emea', 'pacific', or 'china'",
        )

    from vlr.db.session import get_session
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        rows = session.execute(sql_text("""
            WITH team_results AS (
                SELECT t.id AS team_id, t.name AS team_name,
                       t.logo_url, t.country,
                       CASE WHEN m.score_a > m.score_b THEN 1 ELSE 0 END AS won
                FROM matches m
                JOIN teams t ON t.id = m.team_a_id
                WHERE m.match_datetime >= NOW() - (:days || ' days')::interval
                  AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
                  AND t.region = :region

                UNION ALL

                SELECT t.id AS team_id, t.name AS team_name,
                       t.logo_url, t.country,
                       CASE WHEN m.score_b > m.score_a THEN 1 ELSE 0 END AS won
                FROM matches m
                JOIN teams t ON t.id = m.team_b_id
                WHERE m.match_datetime >= NOW() - (:days || ' days')::interval
                  AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
                  AND t.region = :region
            )
            SELECT team_id, team_name,
                   MAX(logo_url) AS logo_url,
                   MAX(country) AS country,
                   COUNT(*) AS played,
                   SUM(won) AS wins,
                   ROUND(100.0 * SUM(won) / NULLIF(COUNT(*), 0), 1) AS win_pct
            FROM team_results
            GROUP BY team_id, team_name
            HAVING COUNT(*) >= :min_matches
            ORDER BY win_pct DESC, played DESC
            LIMIT :limit
        """), {
            "region": region, "days": days,
            "min_matches": min_matches, "limit": limit,
        }).all()

        return [
            {
                "id": int(r[0]),
                "name": r[1],
                "logo_url": r[2],
                "country": r[3],
                "matches_played": int(r[4]),
                "wins": int(r[5]),
                "losses": int(r[4]) - int(r[5]),
                "win_pct": float(r[6]) if r[6] is not None else 0.0,
            }
            for r in rows
        ]
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
    days: int = Query(180, ge=30, le=365),
    min_matches: int = Query(5, ge=1, le=50),
) -> list[dict]:
    """Full leaderboard table for a region. Includes roster, logo, country.

    This powers the redesigned Teams page (bo3-style dense table).
    Returns up to 50 teams per region with their top-5 active roster inline.
    """
    valid = {"americas", "emea", "pacific", "china", "all"}
    if region not in valid:
        raise HTTPException(status_code=400, detail=f"region must be one of {valid}")

    from vlr.db.session import get_session
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        region_filter = "" if region == "all" else "AND t.region = :region"
        params = {"days": days, "min_matches": min_matches, "limit": limit}
        if region != "all":
            params["region"] = region

        team_rows = session.execute(sql_text(f"""
            WITH team_results AS (
                SELECT t.id AS team_id, t.name AS team_name,
                       t.region, t.logo_url, t.country,
                       CASE WHEN m.score_a > m.score_b THEN 1 ELSE 0 END AS won
                FROM matches m
                JOIN teams t ON t.id = m.team_a_id
                WHERE m.match_datetime >= NOW() - (:days || ' days')::interval
                  AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
                  {region_filter}

                UNION ALL

                SELECT t.id AS team_id, t.name AS team_name,
                       t.region, t.logo_url, t.country,
                       CASE WHEN m.score_b > m.score_a THEN 1 ELSE 0 END AS won
                FROM matches m
                JOIN teams t ON t.id = m.team_b_id
                WHERE m.match_datetime >= NOW() - (:days || ' days')::interval
                  AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
                  {region_filter}
            )
            SELECT team_id, team_name,
                   MAX(region) AS region,
                   MAX(logo_url) AS logo_url,
                   MAX(country) AS country,
                   COUNT(*) AS played,
                   SUM(won) AS wins,
                   ROUND(100.0 * SUM(won) / NULLIF(COUNT(*), 0), 1) AS win_pct
            FROM team_results
            GROUP BY team_id, team_name
            HAVING COUNT(*) >= :min_matches
            ORDER BY win_pct DESC, played DESC
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

        return [
            {
                "id": int(r[0]),
                "name": r[1],
                "region": r[2],
                "logo_url": r[3],
                "country": r[4],
                "matches_played": int(r[5]),
                "wins": int(r[6]),
                "losses": int(r[5]) - int(r[6]),
                "win_pct": float(r[7]) if r[7] is not None else 0.0,
                "roster": rosters.get(int(r[0]), []),
            }
            for r in team_rows
        ]
    finally:
        session.close()
