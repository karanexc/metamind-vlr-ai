"""Home / landing page."""
from __future__ import annotations

# --- Bootstrap: make `vlr.*` imports work regardless of how this is launched ---
import sys
from pathlib import Path
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
# --- End bootstrap ---

import streamlit as st

from vlr.app import data
from vlr.app.theme import (
    apply_theme, brand, page_header, section_title, stat_tile, nav_card, match_row,
)

st.set_page_config(
    page_title="VLR Analytics",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


# --- Brand + header -------------------------------------------------------

st.markdown(brand(), unsafe_allow_html=True)
st.markdown(
    page_header(
        "Match intelligence for competitive Valorant",
        "Prediction, performance analysis, and roster intelligence — built from "
        "every Tier 1 and Challengers match since 2024.",
    ),
    unsafe_allow_html=True,
)


# --- Dataset stats --------------------------------------------------------

stats = data.get_database_stats()

st.markdown(section_title("Dataset"), unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        stat_tile(
            "Matches",
            f"{stats.real_matches:,}",
            f"{stats.matches - stats.real_matches:,} forfeits excluded",
            mono=True,
        ),
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        stat_tile("Teams", f"{stats.teams:,}", mono=True),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        stat_tile("Events", f"{stats.events:,}", mono=True),
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        stat_tile(
            "Players",
            f"{stats.players:,}",
            f"{stats.player_rows:,} per-map performances",
            mono=True,
        ),
        unsafe_allow_html=True,
    )

if stats.earliest_match and stats.latest_match:
    st.markdown(
        f'<p style="color:var(--vlr-text-dim); font-size:0.8rem; margin-top:1rem;">'
        f"Data range — {stats.earliest_match.date()} to {stats.latest_match.date()}"
        f"</p>",
        unsafe_allow_html=True,
    )


# --- Nav cards ------------------------------------------------------------

st.markdown(section_title("Tools"), unsafe_allow_html=True)

nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    st.markdown(
        nav_card(
            "▲",
            "Predict a match",
            "Pick two teams and a format. Get win probabilities, projected scoreline, and per-map breakdown.",
        ),
        unsafe_allow_html=True,
    )
    if st.button("Open prediction →", use_container_width=True, key="nav_predict"):
        st.switch_page("pages/1_Predict.py")

with nav_col2:
    st.markdown(
        nav_card(
            "◇",
            "Match analysis",
            "AI-generated breakdown of any past match. Why did they lose, who carried, what swung the result.",
        ),
        unsafe_allow_html=True,
    )
    if st.button("Open analysis →", use_container_width=True, key="nav_analysis"):
        st.switch_page("pages/2_Match_Analysis.py")

with nav_col3:
    st.markdown(
        nav_card(
            "✦",
            "Fantasy mode",
            "Build a custom 5-player roster from any player in the database. Simulate against any team.",
        ),
        unsafe_allow_html=True,
    )
    if st.button("Open fantasy →", use_container_width=True, key="nav_fantasy"):
        st.switch_page("pages/3_Fantasy.py")


# --- Recent matches -------------------------------------------------------

st.markdown(section_title("Recent matches"), unsafe_allow_html=True)

recent = data.get_recent_matches(limit=8)
if recent.empty:
    st.markdown(
        '<div class="vlr-card" style="color:var(--vlr-text-soft);">No recent matches in the database yet.</div>',
        unsafe_allow_html=True,
    )
else:
    rows_html = ""
    for _, row in recent.iterrows():
        date_str = row["datetime"].strftime("%b %d, %Y") if row["datetime"] is not None else "—"
        rows_html += match_row(
            team_a=row["team_a"],
            score_a=int(row["score_a"]),
            team_b=row["team_b"],
            score_b=int(row["score_b"]),
            event=row["event"] or "—",
            date=date_str,
            best_of=int(row["best_of"]) if row["best_of"] else None,
        )
    st.markdown(rows_html, unsafe_allow_html=True)


# --- Top performers -------------------------------------------------------

st.markdown(section_title("Top performers"), unsafe_allow_html=True)

tab_rating, tab_acs, tab_adr = st.tabs(["Rating", "ACS", "ADR"])

with tab_rating:
    df = data.get_top_players("rating", min_maps=30, limit=10)
    if not df.empty:
        df.columns = ["Player", "Maps", "Avg Rating"]
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_acs:
    df = data.get_top_players("acs", min_maps=30, limit=10)
    if not df.empty:
        df.columns = ["Player", "Maps", "Avg ACS"]
        st.dataframe(df, use_container_width=True, hide_index=True)

with tab_adr:
    df = data.get_top_players("adr", min_maps=30, limit=10)
    if not df.empty:
        df.columns = ["Player", "Maps", "Avg ADR"]
        st.dataframe(df, use_container_width=True, hide_index=True)


# --- Footer ---------------------------------------------------------------

st.markdown(
    '<p style="color:var(--vlr-text-dim); font-size:0.75rem; text-align:center; margin-top:4rem;">'
    "Data sourced from vlr.gg · Predictions powered by a custom ML model trained on player-agent-map performance"
    "</p>",
    unsafe_allow_html=True,
)
