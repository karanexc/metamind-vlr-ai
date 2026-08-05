"""Pydantic response schemas for the API.

These define the JSON shape of every endpoint response. The frontend consumes
these — we keep them stable so the JS doesn't break when we tweak internals.
"""
from __future__ import annotations

from datetime import datetime as DateTime
from typing import Optional

from pydantic import BaseModel


# --- Stats / overview ----------------------------------------------------


class DatabaseStats(BaseModel):
    matches: int
    real_matches: int
    teams: int
    events: int
    players: int
    maps: int
    player_rows: int
    earliest_match: Optional[DateTime] = None
    latest_match: Optional[DateTime] = None


# --- Teams ---------------------------------------------------------------


class TeamListItem(BaseModel):
    id: int
    name: str
    n_matches: int
    logo_url: Optional[str] = None


class TeamSummary(BaseModel):
    id: int
    name: str
    n_matches: int
    n_wins: int
    match_win_rate: float
    map_wins: int
    map_total: int
    map_win_rate: float
    roster: list[dict]
    recent_matches: list[dict]
    per_map: list[dict]


# --- Players -------------------------------------------------------------


class PlayerListItem(BaseModel):
    id: int
    name: str
    n_maps: int


class PlayerSummary(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    country: Optional[str] = None
    n_maps: int
    avg_rating: float
    avg_acs: float
    avg_kast: float
    avg_adr: float
    avg_hs: float
    total_kills: int
    total_deaths: int
    per_agent: list[dict]
    per_map: list[dict]
    recent_form: list[dict]


# --- Matches -------------------------------------------------------------


class MatchListItem(BaseModel):
    match_id: int
    team_a: str
    team_b: str
    score_a: int
    score_b: int
    best_of: Optional[int] = None
    stage: Optional[str] = None
    datetime: Optional[DateTime] = None
    event: Optional[str] = None


class PlayerMapStat(BaseModel):
    player: str
    team: Optional[str] = None
    agent: Optional[str] = None
    rating: Optional[float] = None
    acs: Optional[int] = None
    k: Optional[int] = None
    d: Optional[int] = None
    a: Optional[int] = None
    kast: Optional[int] = None
    adr: Optional[float] = None
    hs: Optional[int] = None


class MapDetail(BaseModel):
    index: int
    name: str
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    picked_by: Optional[str] = None
    stats: list[PlayerMapStat]


class MatchDetail(BaseModel):
    match_id: int
    team_a_name: str
    team_b_name: str
    team_a_id: Optional[int] = None
    team_b_id: Optional[int] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    best_of: Optional[int] = None
    stage: Optional[str] = None
    patch: Optional[str] = None
    datetime: Optional[DateTime] = None
    event_name: Optional[str] = None
    event_id: Optional[int] = None
    maps: list[MapDetail]


# --- Predictions ---------------------------------------------------------


class MapPrediction(BaseModel):
    map_name: str
    prob_a: float
    prob_b: float
    confidence: str


class MatchPrediction(BaseModel):
    team_a_name: str
    team_b_name: str
    prob_a: float
    prob_b: float
    predicted_score_a: int
    predicted_score_b: int
    best_of: int
    map_predictions: list[MapPrediction]
    confidence: str
    note: str
    cross_tier_warning: Optional[str] = None


class PredictRequest(BaseModel):
    team_a_id: int
    team_b_id: int
    best_of: int = 3


class FantasyRequest(BaseModel):
    team_a_players: list[str]
    team_b_players: list[str]
    best_of: int = 3


# --- Analysis (LLM) ------------------------------------------------------


class LossAnalysis(BaseModel):
    summary: str
    key_factors: list[str]
    standout_players: list[str]
    underperformers: list[str]


# --- Top players ---------------------------------------------------------


class TopPlayer(BaseModel):
    player: str
    n_maps: int
    avg_metric: float


# --- Live scrape ---------------------------------------------------------


class LiveStatus(BaseModel):
    enabled: bool
    interval_minutes: int
    status: str
    running: bool = False
    last_run: Optional[str] = None
    last_result: Optional[dict] = None
    next_run: Optional[str] = None


class RefreshResult(BaseModel):
    status: str
    started: bool = False


# --- Pick'em / event forecast --------------------------------------------


class EventTeam(BaseModel):
    id: int
    name: str


class PickemRequest(BaseModel):
    team_ids: list[int]
    best_of: int = 3
    n_sims: int = 20000


class PickemForecastItem(BaseModel):
    team_id: int
    team_name: str
    champion_prob: float
    expected_wins: float
    win_rate: float
    avg_win_prob: float


class PickemForecast(BaseModel):
    format: str
    best_of: int
    n_sims: int
    n_teams: int
    teams: list[PickemForecastItem]
    unavailable: list[str]
    note: str = ""


# --- Agent meta ----------------------------------------------------------


class AgentMetaItem(BaseModel):
    agent: str
    picks: int
    pick_rate: float
    win_rate: float
    avg_rating: float
    avg_acs: float


# --- Player depth analysis -----------------------------------------------


class EventPlayer(BaseModel):
    id: int
    name: str
    n_maps: int


class PlayerEventMap(BaseModel):
    index: int
    map_name: Optional[str] = None
    opponent: Optional[str] = None
    agent: Optional[str] = None
    rating: float
    acs: int
    kills: int
    deaths: int
    kast: int
    adr: float
    hs: int
    won: bool
    stage: Optional[str] = None


class PlayerEventAgent(BaseModel):
    agent: str
    maps: int
    avg_rating: float
    avg_acs: float


class PlayerEventAnalysis(BaseModel):
    player_id: int
    player_name: str
    event_id: int
    event_name: str
    n_maps: int
    map_wins: int
    map_win_rate: float
    avg_rating: float
    avg_acs: float
    avg_kast: float
    avg_adr: float
    avg_hs: float
    total_kills: int
    total_deaths: int
    series: list[PlayerEventMap]
    per_agent: list[PlayerEventAgent]
