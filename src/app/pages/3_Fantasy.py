"""Fantasy mode page."""
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

st.set_page_config(page_title="Fantasy — VLR Analytics", page_icon="●", layout="wide")
apply_theme()


st.markdown(brand(), unsafe_allow_html=True)
st.markdown(
    page_header(
        "Fantasy mode",
        "Build a custom 5-player roster from any player in the database. "
        "Simulate against another custom roster or a real team.",
    ),
    unsafe_allow_html=True,
)


players = data.get_player_options(min_maps=20)
if not players:
    st.error("Not enough player data yet.")
    st.stop()

player_labels = [f"{name}  ·  {n} maps" for _, name, n in players]
player_lookup = {label: (pid, name) for label, (pid, name, _) in zip(player_labels, players)}


# --- Mode selector --------------------------------------------------------

st.markdown(section_title("Setup"), unsafe_allow_html=True)
mode = st.radio(
    "Opponent",
    ["Custom Team A vs Custom Team B", "Custom Team vs Real Team"],
    horizontal=True,
    label_visibility="collapsed",
)


# --- Team A ---------------------------------------------------------------

st.markdown(
    '<div style="font-size:0.95rem; font-weight:600; color:var(--vlr-text); margin-top:1.5rem; margin-bottom:0.5rem;">Team A — Custom roster</div>',
    unsafe_allow_html=True,
)
team_a_picks = st.multiselect("Pick 5 players", player_labels, max_selections=5, key="fantasy_a", label_visibility="collapsed")
team_a_names = [player_lookup[p][1] for p in team_a_picks]


# --- Team B ---------------------------------------------------------------

team_b_names: list[str] = []
team_b_real_name = ""

if mode == "Custom Team A vs Custom Team B":
    st.markdown(
        '<div style="font-size:0.95rem; font-weight:600; color:var(--vlr-text); margin-top:1.5rem; margin-bottom:0.5rem;">Team B — Custom roster</div>',
        unsafe_allow_html=True,
    )
    available_b = [p for p in player_labels if p not in team_a_picks]
    team_b_picks = st.multiselect("Pick 5 players", available_b, max_selections=5, key="fantasy_b", label_visibility="collapsed")
    team_b_names = [player_lookup[p][1] for p in team_b_picks]
else:
    st.markdown(
        '<div style="font-size:0.95rem; font-weight:600; color:var(--vlr-text); margin-top:1.5rem; margin-bottom:0.5rem;">Team B — Real team</div>',
        unsafe_allow_html=True,
    )
    teams = data.get_team_options(min_matches=10)
    team_labels = [f"{name}  ·  {n} matches" for _, name, n in teams]
    team_lookup = {label: (tid, name) for label, (tid, name, _) in zip(team_labels, teams)}
    b_real_label = st.selectbox("Team", team_labels, key="fantasy_b_real", label_visibility="collapsed")
    _, team_b_real_name = team_lookup[b_real_label]


# --- Format + run --------------------------------------------------------

col_bo, col_spacer, col_btn = st.columns([2, 3, 2])
with col_bo:
    best_of = st.selectbox("Format", [1, 3, 5], index=1, key="fantasy_bo")
with col_btn:
    st.markdown('<div style="padding-top:1.85rem;"></div>', unsafe_allow_html=True)
    run = st.button("Simulate", type="primary", use_container_width=True, key="fantasy_run")


# --- Validation ----------------------------------------------------------

if not run:
    if len(team_a_picks) < 5 or (mode.endswith("Custom Team B") and len(team_b_names) < 5):
        st.markdown(
            '<p style="color:var(--vlr-text-soft); margin-top:2rem; font-size:0.9rem;">'
            "Build full 5-player roster(s) and press <b style='color:var(--vlr-text);'>Simulate</b>."
            "</p>",
            unsafe_allow_html=True,
        )
    st.stop()

if len(team_a_picks) < 5:
    st.error("Team A needs 5 players.")
    st.stop()

if mode.endswith("Custom Team B") and len(team_b_names) < 5:
    st.error("Team B needs 5 players.")
    st.stop()


# --- Run simulation ------------------------------------------------------

if mode.endswith("Custom Team B"):
    prediction = predict.predict_fantasy(team_a_names, team_b_names, best_of=best_of)
    a_label = "Custom Team A"
    b_label = "Custom Team B"
else:
    prediction = predict.predict_match(
        team_a_name="Custom Team A",
        team_b_name=team_b_real_name,
        best_of=best_of,
    )
    a_label = "Custom Team A"
    b_label = team_b_real_name


# --- Roster display ------------------------------------------------------

st.markdown(section_title("Rosters"), unsafe_allow_html=True)

roster_a_html = "<br>".join([f"<span style='color:var(--vlr-text);'>•</span> &nbsp;{n}" for n in team_a_names])
if mode.endswith("Custom Team B"):
    roster_b_html = "<br>".join([f"<span style='color:var(--vlr-text);'>•</span> &nbsp;{n}" for n in team_b_names])
else:
    roster_b_html = f"<i style='color:var(--vlr-text-soft);'>Real-team roster ({b_label})</i>"

st.markdown(
    f'''
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
        <div class="vlr-card">
            <div class="vlr-eyebrow" style="margin-bottom:0.75rem;">{a_label}</div>
            <div style="font-size:0.92rem; line-height:1.9; color:var(--vlr-text-soft);">{roster_a_html}</div>
        </div>
        <div class="vlr-card">
            <div class="vlr-eyebrow" style="margin-bottom:0.75rem;">{b_label}</div>
            <div style="font-size:0.92rem; line-height:1.9; color:var(--vlr-text-soft);">{roster_b_html}</div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# --- Outcome --------------------------------------------------------------

st.markdown(section_title("Simulated outcome"), unsafe_allow_html=True)
st.markdown(
    prediction_hero(
        team_a=a_label,
        team_b=b_label,
        prob_a=prediction.prob_a,
        prob_b=prediction.prob_b,
        score_a=prediction.predicted_score_a,
        score_b=prediction.predicted_score_b,
        best_of=best_of,
        confidence=prediction.confidence,
    ),
    unsafe_allow_html=True,
)


# --- Per-map --------------------------------------------------------------

st.markdown(section_title("Per-map prediction"), unsafe_allow_html=True)
map_cols = st.columns(len(prediction.map_predictions))
for col, mp in zip(map_cols, prediction.map_predictions):
    with col:
        st.markdown(
            map_prediction_card(mp.map_name, mp.prob_a, mp.prob_b, mp.confidence),
            unsafe_allow_html=True,
        )

st.markdown(
    note(
        "<b>Note</b> &nbsp;·&nbsp; Fantasy simulation is a placeholder. Once the prediction model "
        "is wired in, it'll evaluate custom rosters using actual player-agent-map performance data."
    ),
    unsafe_allow_html=True,
)
