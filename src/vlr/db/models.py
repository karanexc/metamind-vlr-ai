"""SQLAlchemy 2.x declarative models.

Schema covers: teams, events, matches, maps_played, veto_actions,
players, and player_map_stats. Per-round / economy data is still future work.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    # vlr.gg's team id (from /team/<id>/...)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(64))
    logo_url: Mapped[Optional[str]] = mapped_column(String(512))
    country: Mapped[Optional[str]] = mapped_column(String(64))
    # Official vlr.gg ranking (from /rankings) — rating, rank-in-region, W-L.
    vlr_rating: Mapped[Optional[int]] = mapped_column(Integer)
    vlr_rank: Mapped[Optional[int]] = mapped_column(Integer)
    vlr_record: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    # Tier classification: 'international', 'tier1', 'tier2', or NULL if unclassified.
    # Populated by `vlr.ml.tiers.classify_event_tier()` based on the event name.
    tier: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Player(Base):
    __tablename__ = "players"

    # vlr.gg's player id (from /player/<id>/...)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(512))
    country: Mapped[Optional[str]] = mapped_column(String(64))
    real_name: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("events.id"))
    team_a_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("teams.id"))
    team_b_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("teams.id"))

    team_a_name: Mapped[str] = mapped_column(String(255))
    team_b_name: Mapped[str] = mapped_column(String(255))
    score_a: Mapped[Optional[int]] = mapped_column(Integer)
    score_b: Mapped[Optional[int]] = mapped_column(Integer)
    best_of: Mapped[Optional[int]] = mapped_column(Integer)

    stage: Mapped[Optional[str]] = mapped_column(String(255))
    patch: Mapped[Optional[str]] = mapped_column(String(32))
    match_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    veto_raw: Mapped[Optional[str]] = mapped_column(Text)

    url: Mapped[str] = mapped_column(String(512), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    event = relationship("Event")
    team_a = relationship("Team", foreign_keys=[team_a_id])
    team_b = relationship("Team", foreign_keys=[team_b_id])
    maps = relationship("MapPlayed", back_populates="match", cascade="all, delete-orphan")
    veto_actions = relationship("VetoAction", back_populates="match", cascade="all, delete-orphan")
    player_stats = relationship(
        "PlayerMapStat", back_populates="match", cascade="all, delete-orphan"
    )


class MapPlayed(Base):
    __tablename__ = "maps_played"
    __table_args__ = (UniqueConstraint("match_id", "map_index", name="uq_map_per_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matches.id"), nullable=False)
    map_index: Mapped[int] = mapped_column(Integer, nullable=False)
    map_name: Mapped[str] = mapped_column(String(64), nullable=False)
    score_a: Mapped[Optional[int]] = mapped_column(Integer)
    score_b: Mapped[Optional[int]] = mapped_column(Integer)
    picked_by: Mapped[Optional[str]] = mapped_column(String(255))

    match = relationship("Match", back_populates="maps")
    player_stats = relationship(
        "PlayerMapStat", back_populates="map_played", cascade="all, delete-orphan"
    )


class VetoAction(Base):
    __tablename__ = "veto_actions"
    __table_args__ = (
        UniqueConstraint("match_id", "order_index", name="uq_veto_order_per_match"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matches.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    team_name: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(32))
    map_name: Mapped[str] = mapped_column(String(64))

    match = relationship("Match", back_populates="veto_actions")


class PlayerMapStat(Base):
    """One row per (map, player). 10 rows per map (5 per team)."""

    __tablename__ = "player_map_stats"
    __table_args__ = (
        UniqueConstraint("map_id", "player_id", name="uq_player_per_map"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("matches.id"), nullable=False)
    map_id: Mapped[int] = mapped_column(Integer, ForeignKey("maps_played.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("players.id"), nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("teams.id"))
    team_name: Mapped[Optional[str]] = mapped_column(String(255))

    agent: Mapped[Optional[str]] = mapped_column(String(64))
    rating: Mapped[Optional[float]] = mapped_column(Float)
    acs: Mapped[Optional[int]] = mapped_column(Integer)
    kills: Mapped[Optional[int]] = mapped_column(Integer)
    deaths: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    plus_minus: Mapped[Optional[int]] = mapped_column(Integer)
    kast: Mapped[Optional[int]] = mapped_column(Integer)  # percentage 0-100
    adr: Mapped[Optional[float]] = mapped_column(Float)
    hs_pct: Mapped[Optional[int]] = mapped_column(Integer)  # percentage 0-100
    fk: Mapped[Optional[int]] = mapped_column(Integer)
    fd: Mapped[Optional[int]] = mapped_column(Integer)
    fk_fd_diff: Mapped[Optional[int]] = mapped_column(Integer)

    match = relationship("Match", back_populates="player_stats")
    map_played = relationship("MapPlayed", back_populates="player_stats")
    player = relationship("Player")
    team = relationship("Team")


class MatchFeatureSnapshot(Base):
    """Cached point-in-time feature vector for a match.

    Populated by `vlr.ml.features.compute_and_cache_features()`. Used as input
    to the XGBoost predictor.
    """

    __tablename__ = "match_feature_snapshots"

    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id"), primary_key=True
    )
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    match = relationship("Match")


class MatchAnalysisCache(Base):
    """Cached LLM-generated analysis for a match.

    The analysis is expensive (~$0.005 + 2-5 seconds per call). We cache it so
    that opening the Match Analysis page for the same match is instant after
    the first view. Click "regenerate" in the UI to force a fresh call.
    """

    __tablename__ = "match_analysis_cache"

    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id"), primary_key=True
    )
    # Full structured analysis as JSON: summary, key_factors, standouts,
    # underperformers, framing, model_used, prompt_version
    analysis: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(16), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    match = relationship("Match")


# --- VCT esports telemetry (historical ability data) ---------------------
# Separate, self-contained tables fed by `vlr.vct` from Riot's public VCT
# dataset (2022-2024). Decoupled from the live vlr scrape — no FKs into the
# vlr tables; players link to the live data by handle/name at query time.


class VctGame(Base):
    """One imported VCT esports game (map), keyed by Riot's platformGameId."""

    __tablename__ = "vct_games"

    game_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)  # game-changers / vct-challengers / vct-international
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    map_name: Mapped[Optional[str]] = mapped_column(String(64))
    played_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_rounds: Mapped[Optional[int]] = mapped_column(Integer)
    team_a_tag: Mapped[Optional[str]] = mapped_column(String(64))
    team_b_tag: Mapped[Optional[str]] = mapped_column(String(64))
    winner_tag: Mapped[Optional[str]] = mapped_column(String(64))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    ability_stats = relationship(
        "VctAbilityStat", back_populates="game", cascade="all, delete-orphan"
    )


class VctAbilityStat(Base):
    """Per (game, player) derived ability + ultimate usage from Riot telemetry."""

    __tablename__ = "vct_ability_stats"
    __table_args__ = (
        UniqueConstraint("game_id", "handle", name="uq_vct_player_per_game"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("vct_games.game_id"), nullable=False)
    handle: Mapped[str] = mapped_column(String(128), nullable=False)   # full in-game name, e.g. "SMG Yoky"
    player_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # tag stripped, for linking
    team_tag: Mapped[Optional[str]] = mapped_column(String(64))
    agent: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    role: Mapped[Optional[str]] = mapped_column(String(32))
    rounds: Mapped[Optional[int]] = mapped_column(Integer)
    # Derived from state snapshots (charge decrements within rounds).
    ability_casts: Mapped[int] = mapped_column(Integer, default=0)   # ability_1 + ability_2 + grenade
    ult_casts: Mapped[int] = mapped_column(Integer, default=0)
    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    won: Mapped[bool] = mapped_column(default=False)

    game = relationship("VctGame", back_populates="ability_stats")


class VctRound(Base):
    """One row per (game, round): outcome + per-team utility/ult + a compact
    event timeline (casts, ults, kills, spike). Powers the round-impact and
    timeline views."""

    __tablename__ = "vct_rounds"
    __table_args__ = (
        UniqueConstraint("game_id", "round_number", name="uq_vct_round_per_game"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(64), ForeignKey("vct_games.game_id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_tag: Mapped[Optional[str]] = mapped_column(String(64))
    win_condition: Mapped[Optional[str]] = mapped_column(String(32))  # ELIMINATION / SPIKE_DEFUSE / DETONATE / ...
    attacker_tag: Mapped[Optional[str]] = mapped_column(String(64))
    winner_util: Mapped[int] = mapped_column(Integer, default=0)
    loser_util: Mapped[int] = mapped_column(Integer, default=0)
    winner_ults: Mapped[int] = mapped_column(Integer, default=0)
    loser_ults: Mapped[int] = mapped_column(Integer, default=0)
    opening_kill_tag: Mapped[Optional[str]] = mapped_column(String(64))
    spike_planted: Mapped[bool] = mapped_column(default=False)
    spike_defused: Mapped[bool] = mapped_column(default=False)
    is_pistol: Mapped[bool] = mapped_column(default=False)
    is_map_point: Mapped[bool] = mapped_column(default=False)
    is_clutch: Mapped[bool] = mapped_column(default=False)
    # Agent that got the round's opening kill (first-blood impact).
    opening_kill_agent: Mapped[Optional[str]] = mapped_column(String(64))
    # Ultimates used this round with outcome: [{"agent": str, "won": bool}] (ult conversion).
    ult_agents: Mapped[Optional[dict]] = mapped_column(JSONB)
    # Compact timeline: [{"t": sec_into_round, "k": ability|ult|kill|plant|defuse, "team": 0|1, "slot"?}]
    timeline: Mapped[Optional[dict]] = mapped_column(JSONB)

    game = relationship("VctGame")
