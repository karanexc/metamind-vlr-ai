"""Feature engineering for match prediction.

The cardinal rule: **point-in-time correctness**. Features for a match on
2024-08-15 may ONLY use data from matches that completed before that date.
Violating this leaks future information backward and inflates test accuracy.

Every public function in this module accepts an `as_of` parameter or
operates on a single match's `match_datetime` to enforce the cutoff.

Feature categories:
- Career features: a player's all-time average rating, ACS, KAST, ADR, HS%
- Recent-form features: same metrics restricted to last 60 days
- Agent specialization: per-agent rating averaged over recent maps
- Map specialization: per-map rating averaged over recent maps
- Sample-size flags: how many maps backed each estimate, lets the model
  decide when to trust small-sample features

Team-level features are computed by averaging the 5 players in the lineup.
This is roster-aware by design: a team's "features" depend on who plays,
not on the team's historical aggregate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, text as sql_text
from sqlalchemy.orm import Session

from ..db.models import MapPlayed, Match, Player, PlayerMapStat
from ..db.session import get_session

log = logging.getLogger(__name__)


# --- Constants ------------------------------------------------------------

RECENT_WINDOW_DAYS = 60
MIN_OBS_CAREER = 5      # below this, treat as missing
MIN_OBS_RECENT = 3
MIN_OBS_AGENT = 3
MIN_OBS_MAP = 3

# A neutral baseline used when sample size is too small
NEUTRAL_RATING = 1.0
NEUTRAL_ACS = 200.0
NEUTRAL_KAST = 70.0
NEUTRAL_ADR = 130.0
NEUTRAL_HS = 22.0


# --- Dataclasses ----------------------------------------------------------


@dataclass
class PlayerFeatures:
    """Numeric features describing a single player at a point in time."""
    player_id: int
    as_of: datetime

    # Career
    career_rating: float
    career_acs: float
    career_kast: float
    career_adr: float
    career_hs_pct: float
    career_n_maps: int

    # Recent form (last RECENT_WINDOW_DAYS)
    recent_rating: float
    recent_acs: float
    recent_kast: float
    recent_adr: float
    recent_hs_pct: float
    recent_n_maps: int

    # Form delta: recent vs career rating
    form_delta: float
    # Sample size flag — 1.0 if we have enough data, fades to 0 below threshold
    career_sample_flag: float
    recent_sample_flag: float

    # Tier-conditioned career averages (NEW in 7b)
    # Rating against each tier of opposition — addresses strength-of-schedule bias.
    # A player who averages 1.30 against tier2 isn't equivalent to one averaging
    # 1.30 against international opposition.
    rating_vs_international: float
    rating_vs_tier1: float
    rating_vs_tier2: float
    n_maps_vs_international: int
    n_maps_vs_tier1: int
    n_maps_vs_tier2: int
    # Avg numeric tier of recent opponents (3=international, 2=tier1, 1=tier2).
    # A high value means the player has been playing strong opposition recently.
    avg_recent_opp_tier: float

    def to_dict(self, prefix: str = "") -> dict[str, float]:
        return {
            f"{prefix}career_rating": self.career_rating,
            f"{prefix}career_acs": self.career_acs,
            f"{prefix}career_kast": self.career_kast,
            f"{prefix}career_adr": self.career_adr,
            f"{prefix}career_hs_pct": self.career_hs_pct,
            f"{prefix}career_n_maps": float(self.career_n_maps),
            f"{prefix}recent_rating": self.recent_rating,
            f"{prefix}recent_acs": self.recent_acs,
            f"{prefix}recent_kast": self.recent_kast,
            f"{prefix}recent_adr": self.recent_adr,
            f"{prefix}recent_hs_pct": self.recent_hs_pct,
            f"{prefix}recent_n_maps": float(self.recent_n_maps),
            f"{prefix}form_delta": self.form_delta,
            f"{prefix}career_sample_flag": self.career_sample_flag,
            f"{prefix}recent_sample_flag": self.recent_sample_flag,
            f"{prefix}rating_vs_international": self.rating_vs_international,
            f"{prefix}rating_vs_tier1": self.rating_vs_tier1,
            f"{prefix}rating_vs_tier2": self.rating_vs_tier2,
            f"{prefix}n_maps_vs_international": float(self.n_maps_vs_international),
            f"{prefix}n_maps_vs_tier1": float(self.n_maps_vs_tier1),
            f"{prefix}n_maps_vs_tier2": float(self.n_maps_vs_tier2),
            f"{prefix}avg_recent_opp_tier": self.avg_recent_opp_tier,
        }


@dataclass
class TeamFeatures:
    """Team-level features = aggregate of the 5 lineup players."""
    avg_rating: float
    avg_acs: float
    avg_kast: float
    avg_adr: float
    avg_hs_pct: float
    avg_recent_rating: float
    avg_recent_acs: float
    avg_form_delta: float
    star_rating: float       # the best player on the team
    weakest_rating: float    # the weakest
    rating_spread: float     # star - weakest, measures team balance
    avg_career_n_maps: float
    avg_recent_n_maps: float

    # Tier-aggregated (NEW in 7b)
    avg_rating_vs_international: float
    avg_rating_vs_tier1: float
    avg_rating_vs_tier2: float
    avg_n_maps_vs_international: float
    avg_n_maps_vs_tier1: float
    avg_n_maps_vs_tier2: float
    avg_recent_opp_tier: float

    def to_dict(self, prefix: str = "team_") -> dict[str, float]:
        return {
            f"{prefix}avg_rating": self.avg_rating,
            f"{prefix}avg_acs": self.avg_acs,
            f"{prefix}avg_kast": self.avg_kast,
            f"{prefix}avg_adr": self.avg_adr,
            f"{prefix}avg_hs_pct": self.avg_hs_pct,
            f"{prefix}avg_recent_rating": self.avg_recent_rating,
            f"{prefix}avg_recent_acs": self.avg_recent_acs,
            f"{prefix}avg_form_delta": self.avg_form_delta,
            f"{prefix}star_rating": self.star_rating,
            f"{prefix}weakest_rating": self.weakest_rating,
            f"{prefix}rating_spread": self.rating_spread,
            f"{prefix}avg_career_n_maps": self.avg_career_n_maps,
            f"{prefix}avg_recent_n_maps": self.avg_recent_n_maps,
            f"{prefix}avg_rating_vs_international": self.avg_rating_vs_international,
            f"{prefix}avg_rating_vs_tier1": self.avg_rating_vs_tier1,
            f"{prefix}avg_rating_vs_tier2": self.avg_rating_vs_tier2,
            f"{prefix}avg_n_maps_vs_international": self.avg_n_maps_vs_international,
            f"{prefix}avg_n_maps_vs_tier1": self.avg_n_maps_vs_tier1,
            f"{prefix}avg_n_maps_vs_tier2": self.avg_n_maps_vs_tier2,
            f"{prefix}avg_recent_opp_tier": self.avg_recent_opp_tier,
        }


# --- Sample-size shrinkage ------------------------------------------------


def _sample_flag(n: int, threshold: int) -> float:
    """Smooth flag in [0, 1]: 0 if n=0, 1 if n>=threshold, linear in between."""
    if n <= 0:
        return 0.0
    if n >= threshold:
        return 1.0
    return n / threshold


# --- Player-level features ------------------------------------------------


def build_player_features(
    session: Session, player_id: int, as_of: datetime
) -> PlayerFeatures:
    """Compute features for one player using ONLY data before `as_of`."""
    recent_cutoff = as_of - timedelta(days=RECENT_WINDOW_DAYS)

    # Career stats (everything before as_of)
    career = session.execute(sql_text("""
        SELECT
            COUNT(*) AS n,
            AVG(pms.rating)::float AS rating,
            AVG(pms.acs)::float AS acs,
            AVG(pms.kast)::float AS kast,
            AVG(pms.adr)::float AS adr,
            AVG(pms.hs_pct)::float AS hs
        FROM player_map_stats pms
        JOIN matches m ON m.id = pms.match_id
        WHERE pms.player_id = :pid
          AND pms.rating IS NOT NULL
          AND m.match_datetime IS NOT NULL
          AND m.match_datetime < :as_of
    """), {"pid": player_id, "as_of": as_of}).first()

    career_n = career[0] if career and career[0] else 0
    if career_n >= MIN_OBS_CAREER:
        career_rating = float(career[1] or NEUTRAL_RATING)
        career_acs = float(career[2] or NEUTRAL_ACS)
        career_kast = float(career[3] or NEUTRAL_KAST)
        career_adr = float(career[4] or NEUTRAL_ADR)
        career_hs = float(career[5] or NEUTRAL_HS)
    else:
        career_rating = NEUTRAL_RATING
        career_acs = NEUTRAL_ACS
        career_kast = NEUTRAL_KAST
        career_adr = NEUTRAL_ADR
        career_hs = NEUTRAL_HS

    # Recent stats (within recent_cutoff to as_of)
    recent = session.execute(sql_text("""
        SELECT
            COUNT(*) AS n,
            AVG(pms.rating)::float AS rating,
            AVG(pms.acs)::float AS acs,
            AVG(pms.kast)::float AS kast,
            AVG(pms.adr)::float AS adr,
            AVG(pms.hs_pct)::float AS hs
        FROM player_map_stats pms
        JOIN matches m ON m.id = pms.match_id
        WHERE pms.player_id = :pid
          AND pms.rating IS NOT NULL
          AND m.match_datetime IS NOT NULL
          AND m.match_datetime < :as_of
          AND m.match_datetime >= :recent_cutoff
    """), {"pid": player_id, "as_of": as_of, "recent_cutoff": recent_cutoff}).first()

    recent_n = recent[0] if recent and recent[0] else 0
    if recent_n >= MIN_OBS_RECENT:
        recent_rating = float(recent[1] or career_rating)
        recent_acs = float(recent[2] or career_acs)
        recent_kast = float(recent[3] or career_kast)
        recent_adr = float(recent[4] or career_adr)
        recent_hs = float(recent[5] or career_hs)
    else:
        # Fall back to career — "no recent data" means "use career as the best estimate"
        recent_rating = career_rating
        recent_acs = career_acs
        recent_kast = career_kast
        recent_adr = career_adr
        recent_hs = career_hs

    form_delta = recent_rating - career_rating

    # Tier-conditioned career ratings (NEW in 7b).
    # For each tier, compute average rating ONLY against opponents from events
    # of that tier. Falls back to career rating if sample size is too small.
    tier_rows = session.execute(sql_text("""
        SELECT
            e.tier,
            COUNT(*) AS n,
            AVG(pms.rating)::float AS rating
        FROM player_map_stats pms
        JOIN matches m ON m.id = pms.match_id
        LEFT JOIN events e ON e.id = m.event_id
        WHERE pms.player_id = :pid
          AND pms.rating IS NOT NULL
          AND m.match_datetime IS NOT NULL
          AND m.match_datetime < :as_of
          AND e.tier IS NOT NULL
        GROUP BY e.tier
    """), {"pid": player_id, "as_of": as_of}).all()

    tier_data = {row[0]: {"n": row[1], "rating": float(row[2] or career_rating)}
                 for row in tier_rows}

    def _tier_rating(tier: str) -> tuple[float, int]:
        d = tier_data.get(tier)
        if d is None or d["n"] < MIN_OBS_CAREER:
            return career_rating, (d["n"] if d else 0)
        return d["rating"], d["n"]

    rating_vs_intl, n_intl = _tier_rating("international")
    rating_vs_t1, n_t1 = _tier_rating("tier1")
    rating_vs_t2, n_t2 = _tier_rating("tier2")

    # Average numeric tier of recent opponents — how strong has this player's
    # recent schedule been? High = playing tough opposition, low = soft schedule.
    recent_opp_tier_row = session.execute(sql_text("""
        SELECT AVG(CASE
            WHEN e.tier = 'international' THEN 3
            WHEN e.tier = 'tier1' THEN 2
            WHEN e.tier = 'tier2' THEN 1
            ELSE NULL
        END)::float AS avg_tier
        FROM player_map_stats pms
        JOIN matches m ON m.id = pms.match_id
        LEFT JOIN events e ON e.id = m.event_id
        WHERE pms.player_id = :pid
          AND pms.rating IS NOT NULL
          AND m.match_datetime IS NOT NULL
          AND m.match_datetime < :as_of
          AND m.match_datetime >= :recent_cutoff
          AND e.tier IS NOT NULL
    """), {"pid": player_id, "as_of": as_of, "recent_cutoff": recent_cutoff}).first()

    avg_recent_opp_tier = (
        float(recent_opp_tier_row[0]) if recent_opp_tier_row and recent_opp_tier_row[0]
        else 0.0
    )

    return PlayerFeatures(
        player_id=player_id,
        as_of=as_of,
        career_rating=career_rating,
        career_acs=career_acs,
        career_kast=career_kast,
        career_adr=career_adr,
        career_hs_pct=career_hs,
        career_n_maps=career_n,
        recent_rating=recent_rating,
        recent_acs=recent_acs,
        recent_kast=recent_kast,
        recent_adr=recent_adr,
        recent_hs_pct=recent_hs,
        recent_n_maps=recent_n,
        form_delta=form_delta,
        career_sample_flag=_sample_flag(career_n, MIN_OBS_CAREER * 4),
        recent_sample_flag=_sample_flag(recent_n, MIN_OBS_RECENT * 3),
        rating_vs_international=rating_vs_intl,
        rating_vs_tier1=rating_vs_t1,
        rating_vs_tier2=rating_vs_t2,
        n_maps_vs_international=n_intl,
        n_maps_vs_tier1=n_t1,
        n_maps_vs_tier2=n_t2,
        avg_recent_opp_tier=avg_recent_opp_tier,
    )


# --- Team-level features --------------------------------------------------


def build_team_features(
    session: Session, player_ids: list[int], as_of: datetime
) -> TeamFeatures:
    """Aggregate 5 player feature vectors into team-level features."""
    if not player_ids:
        return _neutral_team_features()

    player_feats = [
        build_player_features(session, pid, as_of) for pid in player_ids
    ]
    n = len(player_feats)
    ratings = [f.recent_rating for f in player_feats]

    return TeamFeatures(
        avg_rating=sum(f.career_rating for f in player_feats) / n,
        avg_acs=sum(f.career_acs for f in player_feats) / n,
        avg_kast=sum(f.career_kast for f in player_feats) / n,
        avg_adr=sum(f.career_adr for f in player_feats) / n,
        avg_hs_pct=sum(f.career_hs_pct for f in player_feats) / n,
        avg_recent_rating=sum(f.recent_rating for f in player_feats) / n,
        avg_recent_acs=sum(f.recent_acs for f in player_feats) / n,
        avg_form_delta=sum(f.form_delta for f in player_feats) / n,
        star_rating=max(ratings),
        weakest_rating=min(ratings),
        rating_spread=max(ratings) - min(ratings),
        avg_career_n_maps=sum(f.career_n_maps for f in player_feats) / n,
        avg_recent_n_maps=sum(f.recent_n_maps for f in player_feats) / n,
        avg_rating_vs_international=sum(f.rating_vs_international for f in player_feats) / n,
        avg_rating_vs_tier1=sum(f.rating_vs_tier1 for f in player_feats) / n,
        avg_rating_vs_tier2=sum(f.rating_vs_tier2 for f in player_feats) / n,
        avg_n_maps_vs_international=sum(f.n_maps_vs_international for f in player_feats) / n,
        avg_n_maps_vs_tier1=sum(f.n_maps_vs_tier1 for f in player_feats) / n,
        avg_n_maps_vs_tier2=sum(f.n_maps_vs_tier2 for f in player_feats) / n,
        avg_recent_opp_tier=sum(f.avg_recent_opp_tier for f in player_feats) / n,
    )


def _neutral_team_features() -> TeamFeatures:
    return TeamFeatures(
        avg_rating=NEUTRAL_RATING, avg_acs=NEUTRAL_ACS,
        avg_kast=NEUTRAL_KAST, avg_adr=NEUTRAL_ADR, avg_hs_pct=NEUTRAL_HS,
        avg_recent_rating=NEUTRAL_RATING, avg_recent_acs=NEUTRAL_ACS,
        avg_form_delta=0.0,
        star_rating=NEUTRAL_RATING, weakest_rating=NEUTRAL_RATING, rating_spread=0.0,
        avg_career_n_maps=0.0, avg_recent_n_maps=0.0,
        avg_rating_vs_international=NEUTRAL_RATING,
        avg_rating_vs_tier1=NEUTRAL_RATING,
        avg_rating_vs_tier2=NEUTRAL_RATING,
        avg_n_maps_vs_international=0.0,
        avg_n_maps_vs_tier1=0.0,
        avg_n_maps_vs_tier2=0.0,
        avg_recent_opp_tier=0.0,
    )


# --- Lineup lookup --------------------------------------------------------


def get_lineup_for_match(
    session: Session, match_id: int, team_id: int
) -> list[int]:
    """Return the 5 player_ids that played for `team_id` in `match_id`.

    Uses tbody position from PlayerMapStat.team_index if team_id resolution
    wasn't successful. Returns whatever's available — even partial lineups.
    """
    rows = session.execute(sql_text("""
        SELECT DISTINCT pms.player_id
        FROM player_map_stats pms
        WHERE pms.match_id = :mid AND pms.team_id = :tid
    """), {"mid": match_id, "tid": team_id}).all()
    return [r[0] for r in rows]


# --- Match-level features -------------------------------------------------


def build_match_features(session: Session, match_id: int) -> Optional[dict[str, float]]:
    """Build the full feature vector for one match.

    Returns None if the match doesn't have enough information (no datetime,
    no team_ids, no lineups, etc.) to compute features.
    """
    match = session.get(Match, match_id)
    if match is None:
        return None
    if match.match_datetime is None:
        return None
    if match.team_a_id is None or match.team_b_id is None:
        return None

    lineup_a = get_lineup_for_match(session, match_id, match.team_a_id)
    lineup_b = get_lineup_for_match(session, match_id, match.team_b_id)

    if not lineup_a or not lineup_b:
        return None

    as_of = match.match_datetime
    team_a_feats = build_team_features(session, lineup_a, as_of)
    team_b_feats = build_team_features(session, lineup_b, as_of)

    features: dict[str, float] = {}
    features.update(team_a_feats.to_dict(prefix="team_a_"))
    features.update(team_b_feats.to_dict(prefix="team_b_"))

    # Differential features: A minus B. Often more predictive than absolute values.
    a_dict = team_a_feats.to_dict(prefix="")
    b_dict = team_b_feats.to_dict(prefix="")
    for key in a_dict:
        features[f"diff_{key}"] = a_dict[key] - b_dict[key]

    return features


# --- Caching / snapshotting -----------------------------------------------


def compute_and_cache_features(session: Session, match_id: int) -> Optional[dict[str, float]]:
    """Compute features for a match and cache in match_feature_snapshots."""
    features = build_match_features(session, match_id)
    if features is None:
        return None

    # Serialize to JSON-friendly dict
    import json
    session.execute(sql_text("""
        INSERT INTO match_feature_snapshots (match_id, features, computed_at)
        VALUES (:mid, :features, NOW())
        ON CONFLICT (match_id) DO UPDATE
            SET features = EXCLUDED.features,
                computed_at = NOW()
    """), {"mid": match_id, "features": json.dumps(features)})
    session.commit()
    return features


def get_cached_features(session: Session, match_id: int) -> Optional[dict[str, float]]:
    row = session.execute(sql_text("""
        SELECT features FROM match_feature_snapshots WHERE match_id = :mid
    """), {"mid": match_id}).first()
    if row is None:
        return None
    import json
    return json.loads(row[0]) if isinstance(row[0], str) else dict(row[0])


def backfill_features(force: bool = False) -> dict[str, int]:
    """Compute features for every completed match. Skips matches already cached."""
    stats = {"total": 0, "skipped": 0, "computed": 0, "failed": 0}
    session = get_session()
    try:
        # Find all matches with scores (i.e. completed)
        match_rows = session.execute(sql_text("""
            SELECT m.id FROM matches m
            WHERE m.score_a IS NOT NULL AND m.score_b IS NOT NULL
              AND m.match_datetime IS NOT NULL
              AND m.team_a_id IS NOT NULL AND m.team_b_id IS NOT NULL
            ORDER BY m.match_datetime
        """)).all()
        match_ids = [r[0] for r in match_rows]
        stats["total"] = len(match_ids)

        # Which ones already cached?
        if not force:
            existing = session.execute(sql_text(
                "SELECT match_id FROM match_feature_snapshots"
            )).all()
            existing_ids = {r[0] for r in existing}
        else:
            existing_ids = set()

        for i, mid in enumerate(match_ids):
            if mid in existing_ids:
                stats["skipped"] += 1
                continue
            try:
                features = compute_and_cache_features(session, mid)
                if features is None:
                    stats["failed"] += 1
                else:
                    stats["computed"] += 1
                if (i + 1) % 100 == 0:
                    log.info("Processed %d/%d matches", i + 1, len(match_ids))
            except Exception:
                log.exception("Feature computation failed for match %d", mid)
                stats["failed"] += 1
                session.rollback()
    finally:
        session.close()
    return stats
