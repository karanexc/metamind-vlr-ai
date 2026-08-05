"""Player endpoints: list + detail + top performers."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from vlr.app import data
from vlr.api.schemas import PlayerListItem, PlayerSummary, TopPlayer

router = APIRouter()


@router.get("/players", response_model=list[PlayerListItem])
async def list_players(min_maps: int = Query(10, ge=1, le=200)) -> list[PlayerListItem]:
    return [
        PlayerListItem(id=pid, name=name, n_maps=n)
        for pid, name, n in data.get_player_options(min_maps=min_maps)
    ]


@router.get("/players/{player_id}", response_model=PlayerSummary)
async def get_player(player_id: int) -> PlayerSummary:
    summary = data.get_player_summary(player_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

    def _df_to_records(df) -> list[dict]:
        if df is None or df.empty:
            return []
        records = []
        for _, r in df.iterrows():
            rec = {}
            for col, val in r.items():
                if pd.isna(val):
                    rec[col] = None
                elif hasattr(val, "isoformat"):
                    rec[col] = val.isoformat()
                elif isinstance(val, (int, float, str, bool)):
                    rec[col] = val
                else:
                    rec[col] = str(val)
            records.append(rec)
        return records

    return PlayerSummary(
        id=player_id,
        name=summary["name"],
        image_url=summary.get("image_url"),
        country=summary.get("country"),
        n_maps=summary["n_maps"],
        avg_rating=summary["avg_rating"],
        avg_acs=summary["avg_acs"],
        avg_kast=summary["avg_kast"],
        avg_adr=summary["avg_adr"],
        avg_hs=summary["avg_hs"],
        total_kills=summary["total_kills"],
        total_deaths=summary["total_deaths"],
        per_agent=_df_to_records(summary["per_agent"]),
        per_map=_df_to_records(summary["per_map"]),
        recent_form=_df_to_records(summary["recent_form"]),
    )


@router.get("/players/top/{metric}", response_model=list[TopPlayer])
async def top_players(
    metric: str,
    min_maps: int = Query(30, ge=1, le=200),
    limit: int = Query(10, ge=1, le=50),
) -> list[TopPlayer]:
    if metric not in ("rating", "acs", "adr", "kast"):
        raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
    df = data.get_top_players(metric, min_maps=min_maps, limit=limit)
    return [
        TopPlayer(
            player=r["player"],
            n_maps=int(r["n_maps"]),
            avg_metric=float(r["avg_metric"]),
        )
        for _, r in df.iterrows()
    ]
