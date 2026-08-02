"""SHAP attribution for individual match predictions.

For any single match prediction, this returns the features that pushed the
model toward predicting team A wins vs team B wins. This is the "ML
identifies influential factors" piece your critical review described —
the LLM downstream consumes these attributions and turns them into prose.

Using XGBoost's built-in approximate SHAP (`pred_contribs=True`) rather
than the standalone `shap` library to avoid an extra dependency. The
output is identical for tree models.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .model import load_model

log = logging.getLogger(__name__)


@dataclass
class FeatureAttribution:
    """One feature's contribution to a prediction."""
    feature: str
    value: float            # the actual feature value at prediction time
    shap_value: float       # log-odds contribution: + favors team A, - favors team B


@dataclass
class PredictionAttribution:
    """SHAP attribution for a single match prediction."""
    base_value: float                              # model's intercept
    prediction: float                              # the predicted log-odds
    attributions: list[FeatureAttribution]         # sorted by abs(shap_value), desc

    def top(self, n: int = 10) -> list[FeatureAttribution]:
        return self.attributions[:n]

    def top_favoring_a(self, n: int = 5) -> list[FeatureAttribution]:
        """Top features that pushed the model toward predicting team A wins."""
        positive = [a for a in self.attributions if a.shap_value > 0]
        positive.sort(key=lambda a: a.shap_value, reverse=True)
        return positive[:n]

    def top_favoring_b(self, n: int = 5) -> list[FeatureAttribution]:
        """Top features that pushed the model toward predicting team B wins."""
        negative = [a for a in self.attributions if a.shap_value < 0]
        negative.sort(key=lambda a: a.shap_value)
        return negative[:n]


def attribute_prediction(features: dict[str, float]) -> Optional[PredictionAttribution]:
    """Compute SHAP attribution for one feature vector.

    Returns None if the model can't be loaded.
    """
    bundle = load_model()
    if bundle is None:
        return None
    model, feature_cols, _ = bundle

    row = np.array([[features.get(c, 0.0) for c in feature_cols]], dtype=float)

    # XGBoost's pred_contribs=True returns SHAP values + a base_value as the
    # last column. Shape: (1, n_features + 1)
    booster = model.get_booster()
    import xgboost as xgb
    dmatrix = xgb.DMatrix(row, feature_names=feature_cols)
    contribs = booster.predict(dmatrix, pred_contribs=True)

    shap_values = contribs[0, :-1]
    base_value = float(contribs[0, -1])
    prediction = float(base_value + shap_values.sum())

    attributions = [
        FeatureAttribution(
            feature=feature_cols[i],
            value=float(row[0, i]),
            shap_value=float(shap_values[i]),
        )
        for i in range(len(feature_cols))
    ]
    attributions.sort(key=lambda a: abs(a.shap_value), reverse=True)

    return PredictionAttribution(
        base_value=base_value,
        prediction=prediction,
        attributions=attributions,
    )


# --- Human-readable feature labels ---------------------------------------

_FEATURE_LABELS = {
    # Career
    "team_a_avg_rating": "Team A average rating",
    "team_b_avg_rating": "Team B average rating",
    "team_a_avg_recent_rating": "Team A recent form (rating)",
    "team_b_avg_recent_rating": "Team B recent form (rating)",
    "team_a_avg_form_delta": "Team A form trend",
    "team_b_avg_form_delta": "Team B form trend",
    "team_a_star_rating": "Team A star player",
    "team_b_star_rating": "Team B star player",
    "team_a_weakest_rating": "Team A weakest player",
    "team_b_weakest_rating": "Team B weakest player",
    "team_a_rating_spread": "Team A roster balance",
    "team_b_rating_spread": "Team B roster balance",
    # Tier-conditioned
    "team_a_avg_recent_opp_tier": "Team A recent opposition strength",
    "team_b_avg_recent_opp_tier": "Team B recent opposition strength",
    "team_a_avg_rating_vs_international": "Team A rating vs international opponents",
    "team_b_avg_rating_vs_international": "Team B rating vs international opponents",
    "team_a_avg_rating_vs_tier1": "Team A rating vs Tier 1 opponents",
    "team_b_avg_rating_vs_tier1": "Team B rating vs Tier 1 opponents",
    # Differentials
    "diff_avg_rating": "Rating differential",
    "diff_avg_recent_rating": "Recent form differential",
    "diff_avg_form_delta": "Form trend differential",
    "diff_star_rating": "Star player differential",
    "diff_avg_recent_opp_tier": "Opposition strength differential",
    "diff_avg_rating_vs_international": "International experience differential",
    "diff_avg_rating_vs_tier1": "Tier 1 experience differential",
}


def humanize_feature(feature_name: str) -> str:
    """Convert a feature column name to a human-readable label."""
    if feature_name in _FEATURE_LABELS:
        return _FEATURE_LABELS[feature_name]
    # Fallback: prettify the underscore form
    cleaned = feature_name.replace("team_a_", "Team A ").replace("team_b_", "Team B ")
    cleaned = cleaned.replace("diff_", "Differential ").replace("_", " ")
    return cleaned
