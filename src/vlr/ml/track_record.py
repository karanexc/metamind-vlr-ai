"""Prediction track record — the model's calls vs reality, on live vlr matches.

Two sources, both leaning on the point-in-time feature pipeline (features for a
match use ONLY data from before it):
  * backtest — predict recent COMPLETED matches as_of their own date, score vs
    actual. Immediate accuracy numbers. Labelled 'backtest' (the model was
    trained on history, so treat as illustrative, not the honest headline).
  * live — predict UPCOMING matches as_of now (before they're played); the
    result is linked in once the match completes. Leakage-free by construction.

All on the live vlr dataset. Nothing here touches the VCT (2022-24) data.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text as sql_text

from ..db.models import Prediction
from ..db.session import get_session
from ..ml.features import build_team_features
from ..ml.model import load_model, predict_match_proba

log = logging.getLogger(__name__)


def _confidence(prob_a: float) -> str:
    m = abs(prob_a - 0.5)
    return "high" if m > 0.15 else "medium" if m > 0.07 else "low"


def _lineup_asof(session, tid: int, as_of: datetime) -> Optional[list[int]]:
    """The 5 players from this team's most recent COMPLETED match before as_of."""
    row = session.execute(sql_text("""
        SELECT m.id FROM matches m
        WHERE (m.team_a_id = :tid OR m.team_b_id = :tid)
          AND m.score_a IS NOT NULL AND m.score_b IS NOT NULL
          AND (m.match_datetime IS NULL OR m.match_datetime < :as_of)
        ORDER BY m.match_datetime DESC NULLS LAST
        LIMIT 1
    """), {"tid": tid, "as_of": as_of}).first()
    if row is None:
        return None
    players = session.execute(sql_text("""
        SELECT DISTINCT player_id FROM player_map_stats
        WHERE match_id = :mid AND team_id = :tid
        LIMIT 5
    """), {"mid": row[0], "tid": tid}).all()
    ids = [p[0] for p in players]
    return ids or None


def predict_asof(session, team_a_id: int, team_b_id: int,
                 best_of: int, as_of: datetime) -> Optional[dict]:
    """Point-in-time win-probability for A vs B using only data before as_of."""
    if load_model() is None:
        return None
    la = _lineup_asof(session, team_a_id, as_of)
    lb = _lineup_asof(session, team_b_id, as_of)
    if not la or not lb:
        return None
    ta = build_team_features(session, la, as_of)
    tb = build_team_features(session, lb, as_of)
    features: dict = {}
    features.update(ta.to_dict(prefix="team_a_"))
    features.update(tb.to_dict(prefix="team_b_"))
    a, b = ta.to_dict(prefix=""), tb.to_dict(prefix="")
    for k in a:
        features[f"diff_{k}"] = a[k] - b[k]
    return predict_match_proba(features, best_of=best_of)


def _store(session, *, match_id, ta_id, tb_id, ta, tb, event, dt, bo, res,
           source, predicted_at, actual=None):
    pa = res["prob_a"]
    pred_winner = ta if pa >= 0.5 else tb
    row = Prediction(
        match_id=match_id, team_a_id=ta_id, team_b_id=tb_id,
        team_a_name=ta, team_b_name=tb, event_name=event, scheduled_at=dt, best_of=bo,
        prob_a=round(pa, 3), prob_b=round(res["prob_b"], 3),
        predicted_score_a=res.get("predicted_score_a"),
        predicted_score_b=res.get("predicted_score_b"),
        predicted_winner=pred_winner, confidence=_confidence(pa),
        model_version="v1", source=source, predicted_at=predicted_at,
    )
    if actual is not None:
        sa, sb = actual
        aw = ta if sa > sb else tb
        row.actual_score_a, row.actual_score_b = sa, sb
        row.actual_winner = aw
        row.correct = (pred_winner == aw)
        row.completed_at = dt
    session.add(row)
    return pred_winner


def backtest_recent(limit: int = 200) -> dict:
    """Predict the most recent completed matches point-in-time; store vs actual."""
    stats = {"considered": 0, "predicted": 0, "skipped": 0}
    session = get_session()
    try:
        rows = session.execute(sql_text("""
            SELECT m.id, m.team_a_id, m.team_b_id, m.team_a_name, m.team_b_name,
                   m.score_a, m.score_b, m.best_of, m.match_datetime, e.name
            FROM matches m LEFT JOIN events e ON e.id = m.event_id
            WHERE m.score_a IS NOT NULL AND m.score_b IS NOT NULL
              AND m.team_a_id IS NOT NULL AND m.team_b_id IS NOT NULL
              AND m.match_datetime IS NOT NULL
            ORDER BY m.match_datetime DESC
            LIMIT :lim
        """), {"lim": limit}).all()
        for mid, ta_id, tb_id, ta, tb, sa, sb, bo, dt, event in rows:
            stats["considered"] += 1
            if session.get(Prediction, mid):
                stats["skipped"] += 1
                continue
            res = predict_asof(session, ta_id, tb_id, bo or 3, dt)
            if res is None:
                stats["skipped"] += 1
                continue
            _store(session, match_id=mid, ta_id=ta_id, tb_id=tb_id, ta=ta, tb=tb,
                   event=event, dt=dt, bo=bo, res=res, source="backtest",
                   predicted_at=dt, actual=(sa, sb))
            stats["predicted"] += 1
        session.commit()
        return stats
    finally:
        session.close()


def predict_upcoming() -> dict:
    """Predict upcoming matches (in the DB, no result yet) as_of now."""
    stats = {"upcoming": 0, "predicted": 0, "skipped": 0}
    session = get_session()
    try:
        now = datetime.utcnow()
        rows = session.execute(sql_text("""
            SELECT m.id, m.team_a_id, m.team_b_id, m.team_a_name, m.team_b_name,
                   m.best_of, m.match_datetime, e.name
            FROM matches m LEFT JOIN events e ON e.id = m.event_id
            WHERE m.score_a IS NULL
              AND m.team_a_id IS NOT NULL AND m.team_b_id IS NOT NULL
        """)).all()
        for mid, ta_id, tb_id, ta, tb, bo, dt, event in rows:
            stats["upcoming"] += 1
            if session.get(Prediction, mid):
                stats["skipped"] += 1
                continue
            res = predict_asof(session, ta_id, tb_id, bo or 3, now)
            if res is None:
                stats["skipped"] += 1
                continue
            _store(session, match_id=mid, ta_id=ta_id, tb_id=tb_id, ta=ta, tb=tb,
                   event=event, dt=dt, bo=bo, res=res, source="live", predicted_at=now)
            stats["predicted"] += 1
        session.commit()
        return stats
    finally:
        session.close()


def link_results() -> dict:
    """Fill actual result + correctness for predictions whose match completed."""
    stats = {"linked": 0}
    session = get_session()
    try:
        preds = session.execute(
            sql_text("SELECT match_id FROM predictions WHERE correct IS NULL")
        ).all()
        for (mid,) in preds:
            m = session.execute(sql_text("""
                SELECT team_a_name, team_b_name, score_a, score_b, match_datetime
                FROM matches WHERE id = :mid
            """), {"mid": mid}).first()
            if m is None or m[2] is None or m[3] is None:
                continue
            ta, tb, sa, sb, dt = m
            p = session.get(Prediction, mid)
            if p is None:
                continue
            aw = ta if sa > sb else tb
            p.actual_score_a, p.actual_score_b = sa, sb
            p.actual_winner = aw
            p.correct = (p.predicted_winner == aw)
            p.completed_at = dt or datetime.utcnow()
            stats["linked"] += 1
        session.commit()
        return stats
    finally:
        session.close()
