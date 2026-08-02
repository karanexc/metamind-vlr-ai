"""Match prediction page."""
from __future__ import annotations

# --- Bootstrap ---
import sys
from pathlib import Path
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
# --- End bootstrap ---

import streamlit as st

from vlr.app import data, predict
from vlr.app.theme import (
    apply_theme, brand, page_header, section_title,
    prediction_hero, map_prediction_card, note,
)

st.set_page_config(page_title="Predict — VLR Analytics", page_icon="●", layout="wide")
apply_theme()


st.markdown(brand(), unsafe_allow_html=True)
st.markdown(
    page_header(
        "Match prediction",
        "Pick two teams and a format. The model predicts series outcome and per-map win probabilities.",
    ),
    unsafe_allow_html=True,
)


# --- Inputs ---------------------------------------------------------------

teams = data.get_team_options(min_matches=10)
if not teams:
    st.error("No teams in the database. Run a scrape first.")
    st.stop()

team_labels = [f"{name}  ·  {n} matches" for _, name, n in teams]
team_name_lookup = {label: name for label, (_, name, _) in zip(team_labels, teams)}
team_id_lookup = {label: tid for label, (tid, _, _) in zip(team_labels, teams)}


col1, col_vs, col2 = st.columns([5, 1, 5])
with col1:
    a_label = st.selectbox("Team A", team_labels, index=0, key="team_a")
with col_vs:
    st.markdown(
        '<div style="text-align:center; padding-top:2.6rem; '
        'color:var(--vlr-text-dim); font-weight:600; font-family:var(--font-mono); '
        'letter-spacing:0.1em; font-size:0.85rem;">VS</div>',
        unsafe_allow_html=True,
    )
with col2:
    b_label = st.selectbox(
        "Team B", team_labels,
        index=min(1, len(team_labels) - 1), key="team_b",
    )

col_bo, col_spacer, col_btn = st.columns([2, 3, 2])
with col_bo:
    best_of = st.selectbox("Format", [1, 3, 5], index=1)
with col_btn:
    st.markdown('<div style="padding-top:1.85rem;"></div>', unsafe_allow_html=True)
    run = st.button("Predict", type="primary", use_container_width=True)


if a_label == b_label:
    st.warning("Pick two different teams.")
    st.stop()

if not run:
    st.markdown(
        '<p style="color:var(--vlr-text-soft); margin-top:2rem; font-size:0.9rem;">'
        "Press <b style='color:var(--vlr-text);'>Predict</b> to see win probabilities, "
        "projected scoreline, and per-map breakdown."
        "</p>",
        unsafe_allow_html=True,
    )
    st.stop()


team_a_name = team_name_lookup[a_label]
team_b_name = team_name_lookup[b_label]
team_a_id = team_id_lookup[a_label]
team_b_id = team_id_lookup[b_label]

prediction = predict.predict_match(
    team_a_name=team_a_name,
    team_b_name=team_b_name,
    team_a_id=team_a_id,
    team_b_id=team_b_id,
    best_of=best_of,
)


# --- Hero card -------------------------------------------------------------

st.markdown(section_title("Projected outcome"), unsafe_allow_html=True)
st.markdown(
    prediction_hero(
        team_a=team_a_name,
        team_b=team_b_name,
        prob_a=prediction.prob_a,
        prob_b=prediction.prob_b,
        score_a=prediction.predicted_score_a,
        score_b=prediction.predicted_score_b,
        best_of=best_of,
        confidence=prediction.confidence,
    ),
    unsafe_allow_html=True,
)

# Cross-tier warning (only shown when teams have very different opponent histories)
if getattr(prediction, "cross_tier_warning", None):
    st.markdown(
        f'''
        <div style="background:rgba(245, 158, 11, 0.08);
                    border:1px solid rgba(245, 158, 11, 0.3);
                    border-left:3px solid var(--vlr-warning);
                    border-radius:8px;
                    padding:0.85rem 1.1rem;
                    margin-top:1rem;
                    font-size:0.88rem;
                    color:var(--vlr-text-soft);
                    line-height:1.5;">
            <b style="color:var(--vlr-warning);">⚠ Cross-tier matchup</b>
            &nbsp;·&nbsp; {prediction.cross_tier_warning}
        </div>
        ''',
        unsafe_allow_html=True,
    )


# --- Per-map grid ---------------------------------------------------------

st.markdown(section_title("Per-map prediction"), unsafe_allow_html=True)

map_cols = st.columns(len(prediction.map_predictions))
for col, mp in zip(map_cols, prediction.map_predictions):
    with col:
        st.markdown(
            map_prediction_card(mp.map_name, mp.prob_a, mp.prob_b, mp.confidence),
            unsafe_allow_html=True,
        )


# --- Model status note ---------------------------------------------------

st.markdown(
    note(f"<b>Model status</b> &nbsp;·&nbsp; {prediction.note}"),
    unsafe_allow_html=True,
)
