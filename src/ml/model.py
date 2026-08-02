"""XGBoost match prediction model.

The model predicts P(team A wins) for a match given the engineered feature
vector from `vlr.ml.features`.

Evaluation strategy: temporal hold-out. Train on the earliest 80% of matches
by date, test on the latest 20%. This avoids any temporal leakage and
mirrors how the model would be used in production.

Symmetry: features are computed twice per match (A vs B and B vs A with
flipped label), giving the model a chance to learn a symmetric decision
function and doubling training data.
"""
from __future__ import annotations

import json
import logging
import pickle
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text as sql_text

from ..db.session import get_session
from .features import get_cached_features

log = logging.getLogger(__name__)


MODEL_VERSION = "v1"
MODEL_PATH = Path("data/models/xgboost_v1.pkl")


@dataclass
class TrainingResult:
    """Summary of a training run."""
    model_version: str
    n_train: int
    n_test: int
    train_accuracy: float
    test_accuracy: float
    test_log_loss: float
    test_brier: float
    feature_importances: dict[str, float]
    trained_at: str
    notes: str = ""


# --- Data loading ---------------------------------------------------------


def _load_training_data() -> pd.DataFrame:
    """Load every cached feature snapshot with the match's per-map outcomes.

    Returns one row per MAP (not per match). Predicting per-map is finer-
    grained and gives the model ~2.2× more training data (avg maps per match).
    """
    session = get_session()
    try:
        rows = session.execute(sql_text("""
            SELECT
                m.id AS match_id,
                m.match_datetime,
                mp.id AS map_id,
                mp.map_name,
                mp.score_a AS map_score_a,
                mp.score_b AS map_score_b,
                fs.features
            FROM match_feature_snapshots fs
            JOIN matches m ON m.id = fs.match_id
            JOIN maps_played mp ON mp.match_id = m.id
            WHERE mp.score_a IS NOT NULL AND mp.score_b IS NOT NULL
              AND mp.score_a != mp.score_b
              AND m.match_datetime IS NOT NULL
            ORDER BY m.match_datetime
        """)).all()
    finally:
        session.close()

    records = []
    for r in rows:
        try:
            features = json.loads(r.features) if isinstance(r.features, str) else dict(r.features)
        except (TypeError, json.JSONDecodeError):
            continue
        rec = {
            "match_id": r.match_id,
            "match_datetime": r.match_datetime,
            "map_id": r.map_id,
            "map_name": r.map_name,
            "label": 1 if r.map_score_a > r.map_score_b else 0,
            **features,
        }
        records.append(rec)

    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    log.info("Loaded %d map records for training", len(df))
    return df


def _create_symmetric_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Double the dataset by adding the swapped version of each row.

    For each row (A vs B with label L), add a row (B vs A with label 1-L).
    Forces the model to learn that swapping teams should flip the prediction.
    """
    swapped = df.copy()

    # Swap team_a_X <-> team_b_X
    rename = {}
    for col in df.columns:
        if col.startswith("team_a_"):
            rename[col] = "team_b_" + col[len("team_a_"):]
        elif col.startswith("team_b_"):
            rename[col] = "team_a_" + col[len("team_b_"):]
    swapped = swapped.rename(columns=rename)

    # Negate the diff_* features and label
    for col in swapped.columns:
        if col.startswith("diff_"):
            swapped[col] = -swapped[col]
    swapped["label"] = 1 - swapped["label"]

    combined = pd.concat([df, swapped], ignore_index=True)
    log.info("Doubled dataset to %d rows via symmetric augmentation", len(combined))
    return combined


def _feature_columns(df: pd.DataFrame) -> list[str]:
    """All columns that are features (numeric, not label or metadata)."""
    exclude = {"match_id", "match_datetime", "map_id", "map_name", "label"}
    return [c for c in df.columns if c not in exclude]


# --- Training -------------------------------------------------------------


def train_model(test_fraction: float = 0.2) -> TrainingResult:
    """Train an XGBoost classifier on map-level outcomes.

    Uses a temporal split: earliest (1 - test_fraction) of matches train,
    latest test_fraction tests. This prevents data leakage.
    """
    try:
        import xgboost as xgb
        from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
    except ImportError as e:
        raise RuntimeError(
            "xgboost and scikit-learn are required. Install via "
            "`pip install xgboost scikit-learn`."
        ) from e

    df = _load_training_data()
    if df.empty:
        raise RuntimeError(
            "No training data. Run `compute-features` first to populate "
            "match_feature_snapshots."
        )

    # Temporal split BEFORE symmetric augmentation, so the test set only
    # contains real matches (not augmented swaps).
    df = df.sort_values("match_datetime").reset_index(drop=True)
    split_idx = int(len(df) * (1 - test_fraction))
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    log.info(
        "Temporal split: %d train (until %s) / %d test (from %s)",
        len(train_df), train_df["match_datetime"].iloc[-1] if len(train_df) else "?",
        len(test_df), test_df["match_datetime"].iloc[0] if len(test_df) else "?",
    )

    # Augment ONLY the training data (test set stays clean)
    train_df = _create_symmetric_dataset(train_df)

    feature_cols = _feature_columns(df)
    X_train = train_df[feature_cols].astype(float).values
    y_train = train_df["label"].astype(int).values
    X_test = test_df[feature_cols].astype(float).values
    y_test = test_df["label"].astype(int).values

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        reg_lambda=1.0,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_pred = model.predict(X_test)
    test_proba = model.predict_proba(X_test)[:, 1]
    test_acc = accuracy_score(y_test, test_pred)
    test_ll = log_loss(y_test, test_proba)
    test_brier = brier_score_loss(y_test, test_proba)

    log.info(
        "Trained. Train acc=%.3f  Test acc=%.3f  Test log-loss=%.3f  Test Brier=%.3f",
        train_acc, test_acc, test_ll, test_brier,
    )

    importances = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )

    result = TrainingResult(
        model_version=MODEL_VERSION,
        n_train=len(train_df),
        n_test=len(test_df),
        train_accuracy=float(train_acc),
        test_accuracy=float(test_acc),
        test_log_loss=float(test_ll),
        test_brier=float(test_brier),
        feature_importances={f: float(v) for f, v in importances[:20]},
        trained_at=datetime.utcnow().isoformat(),
        notes=f"Temporal split at {1 - test_fraction:.0%}, symmetric augmentation on train",
    )

    # Persist model + metadata
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({
            "model": model,
            "feature_cols": feature_cols,
            "result": asdict(result),
        }, f)
    log.info("Saved model to %s", MODEL_PATH)

    return result


# --- Inference ------------------------------------------------------------


def load_model():
    """Load the trained model from disk. Returns (model, feature_cols, metadata)."""
    if not MODEL_PATH.exists():
        return None
    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)
    return data["model"], data["feature_cols"], data.get("result", {})


def predict_map_proba(features: dict[str, float]) -> Optional[float]:
    """Given a feature dict, return P(team A wins this map)."""
    bundle = load_model()
    if bundle is None:
        return None
    model, feature_cols, _ = bundle
    row = np.array([[features.get(c, 0.0) for c in feature_cols]], dtype=float)
    return float(model.predict_proba(row)[0, 1])


def predict_match_proba(features: dict[str, float], best_of: int = 3) -> Optional[dict]:
    """Predict series outcome via Monte Carlo over per-map probabilities.

    For a Bo3: simulate each map independently with the model's per-map
    probability, count series-level wins across many trials.

    Returns a dict with prob_a, prob_b, predicted_score_a, predicted_score_b.
    """
    p_map = predict_map_proba(features)
    if p_map is None:
        return None

    wins_needed = (best_of + 1) // 2

    # Closed-form for simple case (all maps have same probability for now)
    # Probability of winning at least wins_needed of best_of maps:
    from math import comb
    prob_a_wins_series = sum(
        comb(best_of, k) * (p_map ** k) * ((1 - p_map) ** (best_of - k))
        for k in range(wins_needed, best_of + 1)
    )

    # Predicted scoreline: round expected map wins
    expected_a_wins = best_of * p_map
    if p_map >= 0.5:
        score_a = wins_needed
        score_b = max(0, round(best_of - expected_a_wins))
        score_b = min(score_b, wins_needed - 1)
    else:
        score_b = wins_needed
        score_a = max(0, round(expected_a_wins))
        score_a = min(score_a, wins_needed - 1)

    return {
        "prob_a": float(prob_a_wins_series),
        "prob_b": float(1 - prob_a_wins_series),
        "predicted_score_a": int(score_a),
        "predicted_score_b": int(score_b),
        "per_map_prob_a": float(p_map),
    }


def evaluate_model() -> Optional[dict]:
    """Return the saved evaluation metrics from the last training run."""
    bundle = load_model()
    if bundle is None:
        return None
    return bundle[2]
