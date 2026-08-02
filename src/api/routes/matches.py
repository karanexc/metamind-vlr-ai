"""Match endpoints: recent list + single match detail + event list."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from vlr.app import data
from vlr.api.schemas import MapDetail, MatchDetail, MatchListItem, PlayerMapStat

router = APIRouter()


@router.get("/matches/recent", response_model=list[MatchListItem])
async def recent_matches(limit: int = Query(20, ge=1, le=200)) -> list[MatchListItem]:
    df = data.get_recent_matches(limit=limit)
    return [
        MatchListItem(
            match_id=int(r["match_id"]),
            team_a=r["team_a"], team_b=r["team_b"],
            score_a=int(r["score_a"]), score_b=int(r["score_b"]),
            best_of=int(r["best_of"]) if r["best_of"] is not None else None,
            stage=r["stage"],
            datetime=r["datetime"],
            event=r["event"],
        )
        for _, r in df.iterrows()
    ]


@router.get("/matches/by-tier/{tier}", response_model=list[MatchListItem])
async def matches_by_tier(
    tier: str,
    limit: int = Query(60, ge=1, le=200),
) -> list[MatchListItem]:
    """Recent matches filtered by event tier.

    Valid tier values: international | tier1 | tier2 | all
    """
    if tier not in {"international", "tier1", "tier2", "all"}:
        raise HTTPException(
            status_code=400,
            detail="tier must be 'international', 'tier1', 'tier2', or 'all'",
        )

    from vlr.db.session import get_session
    from sqlalchemy import text as sql_text
    session = get_session()
    try:
        tier_filter = "" if tier == "all" else "AND e.tier = :tier"
        params = {"limit": limit}
        if tier != "all":
            params["tier"] = tier
        rows = session.execute(sql_text(f"""
            SELECT m.id, m.team_a_name, m.team_b_name, m.score_a, m.score_b,
                   m.best_of, m.stage, m.match_datetime, e.name AS event_name
            FROM matches m
            LEFT JOIN events e ON e.id = m.event_id
            WHERE m.score_a IS NOT NULL AND m.score_b IS NOT NULL
              AND (m.score_a > 0 OR m.score_b > 0)
              {tier_filter}
            ORDER BY m.match_datetime DESC NULLS LAST
            LIMIT :limit
        """), params).all()

        return [
            MatchListItem(
                match_id=r[0],
                team_a=r[1], team_b=r[2],
                score_a=r[3] or 0, score_b=r[4] or 0,
                best_of=r[5], stage=r[6],
                datetime=r[7], event=r[8],
            )
            for r in rows
        ]
    finally:
        session.close()


@router.get("/matches/{match_id}", response_model=MatchDetail)
async def get_match(match_id: int) -> MatchDetail:
    detail = data.get_match_detail(match_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    maps = []
    for m in detail["maps"]:
        stats_list = []
        for _, r in m["stats"].iterrows():
            stats_list.append(PlayerMapStat(
                player=r["player"],
                team=r["team"] if r["team"] != r["team"] or r["team"] is None else r["team"],
                agent=r["agent"] if isinstance(r["agent"], str) else None,
                rating=float(r["rating"]) if r["rating"] == r["rating"] and r["rating"] is not None else None,
                acs=int(r["acs"]) if r["acs"] == r["acs"] and r["acs"] is not None else None,
                k=int(r["k"]) if r["k"] == r["k"] and r["k"] is not None else None,
                d=int(r["d"]) if r["d"] == r["d"] and r["d"] is not None else None,
                a=int(r["a"]) if r["a"] == r["a"] and r["a"] is not None else None,
                kast=int(r["kast"]) if r["kast"] == r["kast"] and r["kast"] is not None else None,
                adr=float(r["adr"]) if r["adr"] == r["adr"] and r["adr"] is not None else None,
                hs=int(r["hs"]) if r["hs"] == r["hs"] and r["hs"] is not None else None,
            ))
        maps.append(MapDetail(
            index=m["index"],
            name=m["name"],
            score_a=m["score_a"],
            score_b=m["score_b"],
            picked_by=m["picked_by"],
            stats=stats_list,
        ))

    return MatchDetail(
        match_id=detail["match_id"],
        team_a_name=detail["team_a_name"],
        team_b_name=detail["team_b_name"],
        team_a_id=detail["team_a_id"],
        team_b_id=detail["team_b_id"],
        score_a=detail["score_a"],
        score_b=detail["score_b"],
        best_of=detail["best_of"],
        stage=detail["stage"],
        patch=detail["patch"],
        datetime=detail["datetime"],
        event_name=detail["event_name"],
        event_id=detail["event_id"],
        maps=maps,
    )


@router.get("/events")
async def list_events() -> list[dict]:
    """Lightweight list of events with at least one real match."""
    return [
        {"id": eid, "name": name}
        for eid, name in data.get_event_options()
    ]
