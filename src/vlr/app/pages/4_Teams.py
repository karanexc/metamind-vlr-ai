"""Team explorer page."""
from __future__ import annotations

# --- Bootstrap ---
import sys
from pathlib import Path
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
# --- End bootstrap ---

import streamlit as st

from vlr.app import data
from vlr.app.theme import (
    apply_theme, brand, page_header, section_title,
    stat_tile, match_row, Colors,
)

st.set_page_config(page_title="Teams — VLR Analytics", page_icon="●", layout="wide")
apply_theme()


st.markdown(brand(), unsafe_allow_html=True)
st.markdown(
    page_header(
        "Team explorer",
        "Recent matches, current roster, and per-map win rate for any team in the database.",
    ),
    unsafe_allow_html=True,
)


teams = data.get_team_options(min_matches=5)
if not teams:
    st.error("No teams in the database.")
    st.stop()

team_labels = [f"{name}  ·  {n} matches" for _, name, n in teams]
team_id_lookup = {label: tid for label, (tid, _, _) in zip(team_labels, teams)}

selected = st.selectbox("Team", team_labels)
team_id = team_id_lookup[selected]


summary = data.get_team_summary(team_id)
if summary is None:
    st.error("Could not load team data.")
    st.stop()


# --- Team header ---------------------------------------------------------

st.markdown(
    f'<h2 style="margin-top:2rem; margin-bottom:1.5rem;">{summary["name"]}</h2>',
    unsafe_allow_html=True,
)


# --- Top-level stats -----------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        stat_tile(
            "Matches played", f"{summary['n_matches']:,}",
            f"{summary['n_wins']} wins", mono=True,
        ),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_tile("Match win rate", f"{summary['match_win_rate']}%", "across all events", mono=True),
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        stat_tile(
            "Maps played", f"{summary['map_total']:,}",
            f"{summary['map_wins']} wins", mono=True,
        ),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        stat_tile("Map win rate", f"{summary['map_win_rate']}%", "all maps", mono=True),
        unsafe_allow_html=True,
    )


# --- Roster ---------------------------------------------------------------

if summary["roster"]:
    st.markdown(section_title("Current roster"), unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--vlr-text-soft); font-size:0.85rem; margin-top:-0.5rem;">'
        "Based on the most recent match in the database."
        "</p>",
        unsafe_allow_html=True,
    )

    roster_cols = st.columns(5)
    for col, (player_id, player_name) in zip(roster_cols, summary["roster"][:5]):
        with col:
            st.markdown(
                f'''
                <div class="vlr-roster-card">
                    <div class="vlr-roster-card-label">Player</div>
                    <div class="vlr-roster-card-name">{player_name}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )


# --- Per-map ---------------------------------------------------------

st.markdown(section_title("Map performance"), unsafe_allow_html=True)

if summary["per_map"].empty:
    st.markdown(
        '<div class="vlr-card" style="color:var(--vlr-text-soft);">Not enough map data yet.</div>',
        unsafe_allow_html=True,
    )
else:
    chart_df = summary["per_map"][["map", "win_rate"]].set_index("map")
    st.bar_chart(chart_df, color=Colors.ACCENT, height=320)


# --- Recent matches ------------------------------------------------------

st.markdown(section_title("Recent matches"), unsafe_allow_html=True)

if summary["recent_matches"].empty:
    st.markdown(
        '<div class="vlr-card" style="color:var(--vlr-text-soft);">No recent matches.</div>',
        unsafe_allow_html=True,
    )
else:
    rows_html = ""
    for _, row in summary["recent_matches"].iterrows():
        date_str = row["datetime"].strftime("%b %d, %Y") if row["datetime"] is not None else "—"
        rows_html += match_row(
            team_a=row["team_a"],
            score_a=int(row["score_a"]),
            team_b=row["team_b"],
            score_b=int(row["score_b"]),
            event=row["event"] or "—",
            date=date_str,
            best_of=int(row["best_of"]) if row["best_of"] else None,
            perspective_team=summary["name"],
        )
    st.markdown(rows_html, unsafe_allow_html=True)
