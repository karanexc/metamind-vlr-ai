"""Prediction track record — the model's calls vs actual results (live vlr)."""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from vlr.db.models import Prediction, Team
from vlr.db.session import get_session

router = APIRouter()


def _logos(session, rows: list) -> dict:
    ids = {p.team_a_id for p in rows} | {p.team_b_id for p in rows}
    ids.discard(None)
    out: dict = {}
    if ids:
        for tid, logo in session.execute(
            select(Team.id, Team.logo_url).where(Team.id.in_(ids))
        ).all():
            if logo:
                out[int(tid)] = logo
    return out


def _row(p: Prediction, logos: dict) -> dict:
    return {
        "match_id": p.match_id,
        "team_a": p.team_a_name, "team_b": p.team_b_name,
        "team_a_logo": logos.get(p.team_a_id), "team_b_logo": logos.get(p.team_b_id),
        "event": p.event_name,
        "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
        "best_of": p.best_of,
        "prob_a": p.prob_a, "prob_b": p.prob_b,
        "predicted_winner": p.predicted_winner, "confidence": p.confidence,
        "predicted_score_a": p.predicted_score_a, "predicted_score_b": p.predicted_score_b,
        "source": p.source,
        "actual_score_a": p.actual_score_a, "actual_score_b": p.actual_score_b,
        "actual_winner": p.actual_winner, "correct": p.correct,
    }


@router.get("/predictions/upcoming")
async def predictions_upcoming(limit: int = Query(50, ge=1, le=200)) -> list[dict]:
    """Matches the model has called but that haven't been played/scored yet."""
    session = get_session()
    try:
        rows = session.execute(
            select(Prediction).where(Prediction.correct.is_(None))
            .order_by(Prediction.scheduled_at.asc().nullslast())
            .limit(limit)
        ).scalars().all()
        logos = _logos(session, rows)
        return [_row(p, logos) for p in rows]
    finally:
        session.close()


@router.get("/predictions/results")
async def predictions_results(
    source: str = Query("", max_length=16),
    limit: int = Query(80, ge=1, le=300),
) -> list[dict]:
    """Completed matches we predicted, with predicted vs actual + correctness."""
    session = get_session()
    try:
        q = select(Prediction).where(Prediction.correct.isnot(None))
        if source.strip() in ("live", "backtest"):
            q = q.where(Prediction.source == source.strip())
        q = q.order_by(
            Prediction.completed_at.desc().nullslast(),
            Prediction.scheduled_at.desc().nullslast(),
        ).limit(limit)
        rows = session.execute(q).scalars().all()
        logos = _logos(session, rows)
        return [_row(p, logos) for p in rows]
    finally:
        session.close()


@router.get("/predictions/accuracy")
async def predictions_accuracy() -> dict:
    """Hit-rate (overall / live / backtest) + calibration by confidence band."""
    session = get_session()
    try:
        rows = session.execute(
            select(Prediction.source, Prediction.prob_a, Prediction.prob_b, Prediction.correct)
            .where(Prediction.correct.isnot(None))
        ).all()

        def acc(correct_flags: list) -> dict:
            n = len(correct_flags)
            c = sum(1 for r in correct_flags if r)
            return {"n": n, "correct": c, "hit_rate": round(100 * c / n, 1) if n else 0.0}

        live = [r for s, _, _, r in rows if s == "live"]
        back = [r for s, _, _, r in rows if s == "backtest"]
        allp = [r for _, _, _, r in rows]

        bands = {"50–60": [0, 0], "60–70": [0, 0], "70–80": [0, 0], "80–90": [0, 0], "90–100": [0, 0]}
        for s, pa, pb, r in rows:
            p = max(pa, pb) * 100
            band = ("50–60" if p < 60 else "60–70" if p < 70 else
                    "70–80" if p < 80 else "80–90" if p < 90 else "90–100")
            bands[band][1] += 1
            if r:
                bands[band][0] += 1
        calibration = [
            {"band": k, "n": v[1], "actual_win_rate": round(100 * v[0] / v[1], 1) if v[1] else 0.0}
            for k, v in bands.items()
        ]

        return {"overall": acc(allp), "live": acc(live), "backtest": acc(back), "calibration": calibration}
    finally:
        session.close()
