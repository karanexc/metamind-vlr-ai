"""Data access layer for the Streamlit app.

All DB queries route through here. Heavy queries are cached for 10 minutes
to keep the app snappy without serving stale data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy import desc, func, select, text as sql_text

from vlr.db.models import Event, MapPlayed, Match, Player, PlayerMapStat, Team, VetoAction
from vlr.db.session import get_session

# Forfeits and walkovers have null scores or no maps — exclude them from
# everything that needs real match data.
_REAL_MATCH_FILTER = "score_a IS NOT NULL AND score_b IS NOT NULL"


# --- Database stats ------------------------------------------------------


@dataclass
class DatabaseStats:
    matches: int
    real_matches: int   # excludes forfeits
    teams: int
    events: int
    players: int
    maps: int
    player_rows: int
    earliest_match: Optional[datetime]
    latest_match: Optional[datetime]


@st.cache_data(ttl=600)
def get_database_stats() -> DatabaseStats:
    session = get_session()
    try:
        matches = session.scalar(select(func.count()).select_from(Match)) or 0
        real_matches = session.scalar(
            select(func.count(Match.id)).where(
                Match.score_a.is_not(None), Match.score_b.is_not(None)
            )
        ) or 0
        teams = session.scalar(select(func.count()).select_from(Team)) or 0
        events = session.scalar(select(func.count()).select_from(Event)) or 0
        players = session.scalar(select(func.count()).select_from(Player)) or 0
        maps = session.scalar(select(func.count()).select_from(MapPlayed)) or 0
        player_rows = session.scalar(select(func.count()).select_from(PlayerMapStat)) or 0
        earliest = session.scalar(select(func.min(Match.match_datetime)))
        latest = session.scalar(select(func.max(Match.match_datetime)))
        return DatabaseStats(
            matches=matches,
            real_matches=real_matches,
            teams=teams,
            events=events,
            players=players,
            maps=maps,
            player_rows=player_rows,
            earliest_match=earliest,
            latest_match=latest,
        )
    finally:
        session.close()


# --- Recent matches ------------------------------------------------------


@st.cache_data(ttl=600)
def get_recent_matches(limit: int = 10) -> pd.DataFrame:
    session = get_session()
    try:
        rows = session.execute(
            select(
                Match.id, Match.team_a_name, Match.team_b_name,
                Match.score_a, Match.score_b, Match.best_of, Match.stage,
                Match.match_datetime, Event.name.label("event_name"),
            )
            .outerjoin(Event, Event.id == Match.event_id)
            .where(Match.score_a.is_not(None), Match.score_b.is_not(None))
            .order_by(desc(Match.match_datetime))
            .limit(limit)
        ).all()
        return pd.DataFrame(rows, columns=[
            "match_id", "team_a", "team_b", "score_a", "score_b",
            "best_of", "stage", "datetime", "event",
        ])
    finally:
        session.close()


# --- Event listings ------------------------------------------------------


@st.cache_data(ttl=600)
def get_event_options() -> list[tuple[int, str]]:
    """Return (event_id, name) for all events that have at least one real match."""
    session = get_session()
    try:
        rows = session.execute(
            select(Event.id, Event.name, func.max(Match.match_datetime).label("latest"))
            .join(Match, Match.event_id == Event.id)
            .where(Match.score_a.is_not(None))
            .group_by(Event.id, Event.name)
            .order_by(desc("latest"))
        ).all()
        return [(r[0], r[1]) for r in rows]
    finally:
        session.close()


# --- Team listings -------------------------------------------------------


@st.cache_data(ttl=600)
def get_team_options(min_matches: int = 5) -> list[tuple[int, str, int]]:
    """Teams ordered by match count desc. Returns (team_id, name, n_matches)."""
    session = get_session()
    try:
        rows = session.execute(sql_text(f"""
            SELECT t.id, t.name, COUNT(DISTINCT m.id) AS n_matches
            FROM teams t
            JOIN matches m ON (m.team_a_id = t.id OR m.team_b_id = t.id)
            WHERE {_REAL_MATCH_FILTER}
            GROUP BY t.id, t.name
            HAVING COUNT(DISTINCT m.id) >= :min_matches
            ORDER BY n_matches DESC, t.name ASC
        """), {"min_matches": min_matches}).all()
        return [(r[0], r[1], r[2]) for r in rows]
    finally:
        session.close()


@st.cache_data(ttl=600)
def get_team_summary(team_id: int) -> Optional[dict]:
    """Recent matches + map record + agent comp summary for one team."""
    session = get_session()
    try:
        team = session.get(Team, team_id)
        if team is None:
            return None

        # Match record
        n_matches = session.scalar(sql_text(f"""
            SELECT COUNT(*) FROM matches
            WHERE (team_a_id = :t OR team_b_id = :t) AND {_REAL_MATCH_FILTER}
        """), {"t": team_id}) or 0

        n_wins = session.scalar(sql_text(f"""
            SELECT COUNT(*) FROM matches
            WHERE ((team_a_id = :t AND score_a > score_b)
                OR (team_b_id = :t AND score_b > score_a))
              AND {_REAL_MATCH_FILTER}
        """), {"t": team_id}) or 0

        # Map record
        map_record = session.execute(sql_text(f"""
            SELECT
                SUM(CASE WHEN (m.team_a_id = :t AND mp.score_a > mp.score_b)
                          OR (m.team_b_id = :t AND mp.score_b > mp.score_a)
                          THEN 1 ELSE 0 END) AS map_wins,
                COUNT(*) AS total
            FROM maps_played mp
            JOIN matches m ON m.id = mp.match_id
            WHERE (m.team_a_id = :t OR m.team_b_id = :t)
              AND mp.score_a IS NOT NULL AND mp.score_b IS NOT NULL
        """), {"t": team_id}).first()
        map_wins, map_total = (map_record or (0, 0))

        # Recent matches
        recent = session.execute(sql_text(f"""
            SELECT m.id, m.team_a_name, m.team_b_name, m.score_a, m.score_b,
                   m.match_datetime, e.name AS event_name, m.best_of
            FROM matches m
            LEFT JOIN events e ON e.id = m.event_id
            WHERE (m.team_a_id = :t OR m.team_b_id = :t) AND {_REAL_MATCH_FILTER}
            ORDER BY m.match_datetime DESC NULLS LAST
            LIMIT 10
        """), {"t": team_id}).all()
        recent_df = pd.DataFrame(recent, columns=[
            "match_id", "team_a", "team_b", "score_a", "score_b",
            "datetime", "event", "best_of",
        ])

        # Per-map win rate
        per_map = session.execute(sql_text(f"""
            SELECT mp.map_name,
                   COUNT(*) AS played,
                   SUM(CASE WHEN (m.team_a_id = :t AND mp.score_a > mp.score_b)
                             OR (m.team_b_id = :t AND mp.score_b > mp.score_a)
                             THEN 1 ELSE 0 END) AS wins
            FROM maps_played mp
            JOIN matches m ON m.id = mp.match_id
            WHERE (m.team_a_id = :t OR m.team_b_id = :t)
              AND mp.score_a IS NOT NULL AND mp.score_b IS NOT NULL
            GROUP BY mp.map_name
            HAVING COUNT(*) >= 3
            ORDER BY played DESC
        """), {"t": team_id}).all()
        per_map_df = pd.DataFrame(per_map, columns=["map", "played", "wins"])
        if not per_map_df.empty:
            per_map_df["win_rate"] = (per_map_df["wins"] / per_map_df["played"] * 100).round(1)

        # Current roster — based on most recent match
        roster = []
        if not recent_df.empty:
            latest_match_id = int(recent_df.iloc[0]["match_id"])
            roster_rows = session.execute(sql_text("""
                SELECT DISTINCT p.id, p.name
                FROM player_map_stats pms
                JOIN players p ON p.id = pms.player_id
                WHERE pms.match_id = :mid AND pms.team_id = :tid
            """), {"mid": latest_match_id, "tid": team_id}).all()
            roster = [(r[0], r[1]) for r in roster_rows]

        return {
            "name": team.name,
            "n_matches": n_matches,
            "n_wins": n_wins,
            "match_win_rate": round(n_wins / n_matches * 100, 1) if n_matches else 0,
            "map_wins": map_wins or 0,
            "map_total": map_total or 0,
            "map_win_rate": round((map_wins or 0) / (map_total or 1) * 100, 1) if map_total else 0,
            "recent_matches": recent_df,
            "per_map": per_map_df,
            "roster": roster,
        }
    finally:
        session.close()


# --- Player listings -----------------------------------------------------


@st.cache_data(ttl=600)
def get_player_options(min_maps: int = 10) -> list[tuple[int, str, int]]:
    """Players ordered by maps played. Returns (player_id, name, n_maps)."""
    session = get_session()
    try:
        rows = session.execute(sql_text("""
            SELECT p.id, p.name, COUNT(*) AS n_maps
            FROM player_map_stats pms
            JOIN players p ON p.id = pms.player_id
            WHERE pms.rating IS NOT NULL
            GROUP BY p.id, p.name
            HAVING COUNT(*) >= :min_maps
            ORDER BY n_maps DESC, p.name ASC
        """), {"min_maps": min_maps}).all()
        return [(r[0], r[1], r[2]) for r in rows]
    finally:
        session.close()


@st.cache_data(ttl=600)
def get_player_summary(player_id: int) -> Optional[dict]:
    """Career stats + per-agent + per-map breakdown for a single player."""
    session = get_session()
    try:
        player = session.get(Player, player_id)
        if player is None:
            return None

        # Career
        career = session.execute(sql_text("""
            SELECT
                COUNT(*) AS n_maps,
                AVG(rating)::float AS avg_rating,
                AVG(acs)::float AS avg_acs,
                AVG(kast)::float AS avg_kast,
                AVG(adr)::float AS avg_adr,
                AVG(hs_pct)::float AS avg_hs,
                SUM(kills) AS total_kills,
                SUM(deaths) AS total_deaths
            FROM player_map_stats
            WHERE player_id = :pid AND rating IS NOT NULL
        """), {"pid": player_id}).first()

        # Per-agent
        per_agent = session.execute(sql_text("""
            SELECT
                agent,
                COUNT(*) AS played,
                AVG(rating)::float AS avg_rating,
                AVG(acs)::float AS avg_acs
            FROM player_map_stats
            WHERE player_id = :pid AND rating IS NOT NULL AND agent IS NOT NULL
            GROUP BY agent
            HAVING COUNT(*) >= 3
            ORDER BY played DESC
        """), {"pid": player_id}).all()
        per_agent_df = pd.DataFrame(per_agent, columns=["agent", "played", "avg_rating", "avg_acs"])
        if not per_agent_df.empty:
            per_agent_df["avg_rating"] = per_agent_df["avg_rating"].round(2)
            per_agent_df["avg_acs"] = per_agent_df["avg_acs"].round(0).astype(int)

        # Per-map
        per_map = session.execute(sql_text("""
            SELECT
                mp.map_name,
                COUNT(*) AS played,
                AVG(pms.rating)::float AS avg_rating,
                AVG(pms.acs)::float AS avg_acs
            FROM player_map_stats pms
            JOIN maps_played mp ON mp.id = pms.map_id
            WHERE pms.player_id = :pid AND pms.rating IS NOT NULL
            GROUP BY mp.map_name
            HAVING COUNT(*) >= 3
            ORDER BY played DESC
        """), {"pid": player_id}).all()
        per_map_df = pd.DataFrame(per_map, columns=["map", "played", "avg_rating", "avg_acs"])
        if not per_map_df.empty:
            per_map_df["avg_rating"] = per_map_df["avg_rating"].round(2)
            per_map_df["avg_acs"] = per_map_df["avg_acs"].round(0).astype(int)

        # Recent form — last 20 maps with rating
        recent = session.execute(sql_text("""
            SELECT pms.rating, pms.acs, pms.agent, mp.map_name, m.match_datetime,
                   m.team_a_name, m.team_b_name
            FROM player_map_stats pms
            JOIN maps_played mp ON mp.id = pms.map_id
            JOIN matches m ON m.id = pms.match_id
            WHERE pms.player_id = :pid AND pms.rating IS NOT NULL
            ORDER BY m.match_datetime DESC NULLS LAST
            LIMIT 20
        """), {"pid": player_id}).all()
        recent_df = pd.DataFrame(recent, columns=[
            "rating", "acs", "agent", "map", "datetime", "team_a", "team_b"
        ])

        return {
            "name": player.name,
            "n_maps": career[0] if career else 0,
            "avg_rating": round(career[1], 2) if career and career[1] else 0,
            "avg_acs": round(career[2], 0) if career and career[2] else 0,
            "avg_kast": round(career[3], 0) if career and career[3] else 0,
            "avg_adr": round(career[4], 1) if career and career[4] else 0,
            "avg_hs": round(career[5], 0) if career and career[5] else 0,
            "total_kills": career[6] if career else 0,
            "total_deaths": career[7] if career else 0,
            "per_agent": per_agent_df,
            "per_map": per_map_df,
            "recent_form": recent_df,
        }
    finally:
        session.close()


# --- Match detail --------------------------------------------------------


@st.cache_data(ttl=600)
def get_match_detail(match_id: int) -> Optional[dict]:
    session = get_session()
    try:
        m = session.get(Match, match_id)
        if m is None:
            return None

        maps_rows = session.execute(sql_text("""
            SELECT id, map_index, map_name, score_a, score_b, picked_by
            FROM maps_played
            WHERE match_id = :mid
            ORDER BY map_index
        """), {"mid": match_id}).all()

        maps = []
        for map_id, map_idx, map_name, score_a, score_b, picked_by in maps_rows:
            stats_rows = session.execute(sql_text("""
                SELECT p.name, pms.team_name, pms.agent, pms.rating, pms.acs,
                       pms.kills, pms.deaths, pms.assists, pms.kast, pms.adr, pms.hs_pct
                FROM player_map_stats pms
                JOIN players p ON p.id = pms.player_id
                WHERE pms.map_id = :map_id
                ORDER BY pms.team_name, pms.rating DESC NULLS LAST
            """), {"map_id": map_id}).all()
            maps.append({
                "index": map_idx,
                "name": map_name,
                "score_a": score_a,
                "score_b": score_b,
                "picked_by": picked_by,
                "stats": pd.DataFrame(stats_rows, columns=[
                    "player", "team", "agent", "rating", "acs",
                    "k", "d", "a", "kast", "adr", "hs",
                ]),
            })

        return {
            "match_id": m.id,
            "team_a_name": m.team_a_name,
            "team_b_name": m.team_b_name,
            "team_a_id": m.team_a_id,
            "team_b_id": m.team_b_id,
            "score_a": m.score_a,
            "score_b": m.score_b,
            "best_of": m.best_of,
            "stage": m.stage,
            "patch": m.patch,
            "datetime": m.match_datetime,
            "event_name": m.event.name if m.event else None,
            "event_id": m.event_id,
            "maps": maps,
        }
    finally:
        session.close()


# --- Top players (for home page) ----------------------------------------


@st.cache_data(ttl=600)
def get_top_players(metric: str = "rating", min_maps: int = 30, limit: int = 10) -> pd.DataFrame:
    col_map = {"rating": "rating", "acs": "acs", "adr": "adr", "kast": "kast"}
    col = col_map.get(metric, "rating")
    session = get_session()
    try:
        rows = session.execute(sql_text(f"""
            SELECT p.name,
                   COUNT(*) AS n_maps,
                   AVG(pms.{col})::float AS avg_metric
            FROM player_map_stats pms
            JOIN players p ON p.id = pms.player_id
            WHERE pms.{col} IS NOT NULL
            GROUP BY p.id, p.name
            HAVING COUNT(*) >= :min_maps
            ORDER BY avg_metric DESC NULLS LAST
            LIMIT :limit
        """), {"min_maps": min_maps, "limit": limit}).all()
        df = pd.DataFrame(rows, columns=["player", "n_maps", "avg_metric"])
        if not df.empty:
            df["avg_metric"] = df["avg_metric"].round(2)
        return df
    finally:
        session.close()
