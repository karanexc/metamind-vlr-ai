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
