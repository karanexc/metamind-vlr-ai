"""Player explorer page."""
from __future__ import annotations

# --- Bootstrap ---
import sys
from pathlib import Path
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
# --- End bootstrap ---

import pandas as pd
import streamlit as st

from vlr.app import data
from vlr.app.theme import (
    apply_theme, brand, page_header, section_title,
    stat_tile, Colors,
)

st.set_page_config(page_title="Players — VLR Analytics", page_icon="●", layout="wide")
apply_theme()


st.markdown(brand(), unsafe_allow_html=True)
st.markdown(
    page_header(
        "Player explorer",
        "Career stats, agent specialization, and recent form for any player in the database.",
    ),
    unsafe_allow_html=True,
)


players = data.get_player_options(min_maps=20)
if not players:
    st.error("Not enough player data.")
    st.stop()

player_labels = [f"{name}  ·  {n} maps" for _, name, n in players]
player_id_lookup = {label: pid for label, (pid, _, _) in zip(player_labels, players)}

selected = st.selectbox("Player", player_labels)
player_id = player_id_lookup[selected]


summary = data.get_player_summary(player_id)
if summary is None:
    st.error("Could not load player data.")
    st.stop()


st.markdown(
    f'<h2 style="margin-top:2rem; margin-bottom:1.5rem;">{summary["name"]}</h2>',
    unsafe_allow_html=True,
)


# --- Career stats --------------------------------------------------------

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(
        stat_tile("Rating", f"{summary['avg_rating']:.2f}",
                  f"{summary['n_maps']:,} maps", mono=True),
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        stat_tile("ACS", f"{summary['avg_acs']:.0f}", mono=True),
        unsafe_allow_html=True,
    )
with c3:
    kd = summary['total_kills'] / max(summary['total_deaths'], 1)
    st.markdown(
        stat_tile("K/D", f"{kd:.2f}",
                  f"{summary['total_kills']:,} / {summary['total_deaths']:,}",
                  mono=True),
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        stat_tile("KAST", f"{summary['avg_kast']:.0f}%", mono=True),
        unsafe_allow_html=True,
    )
with c5:
    st.markdown(
        stat_tile("HS%", f"{summary['avg_hs']:.0f}%",
                  f"ADR {summary['avg_adr']:.1f}", mono=True),
        unsafe_allow_html=True,
    )


# --- Agent breakdown -----------------------------------------------------

st.markdown(section_title("Agent specialization"), unsafe_allow_html=True)

if summary["per_agent"].empty:
    st.markdown(
        '<div class="vlr-card" style="color:var(--vlr-text-soft);">Not enough agent data yet.</div>',
        unsafe_allow_html=True,
    )
else:
    col_table, col_chart = st.columns([1, 1])
    with col_table:
        df = summary["per_agent"].copy()
        df.columns = ["Agent", "Maps", "Avg Rating", "Avg ACS"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    with col_chart:
        chart_df = summary["per_agent"][["agent", "avg_rating"]].set_index("agent")
        st.bar_chart(chart_df, color=Colors.ACCENT, height=300)


# --- Map breakdown -------------------------------------------------------

st.markdown(section_title("Map performance"), unsafe_allow_html=True)

if summary["per_map"].empty:
    st.markdown(
        '<div class="vlr-card" style="color:var(--vlr-text-soft);">Not enough map data yet.</div>',
        unsafe_allow_html=True,
    )
else:
    col_table, col_chart = st.columns([1, 1])
    with col_table:
        df = summary["per_map"].copy()
        df.columns = ["Map", "Maps", "Avg Rating", "Avg ACS"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    with col_chart:
        chart_df = summary["per_map"][["map", "avg_rating"]].set_index("map")
        st.bar_chart(chart_df, color=Colors.ACCENT, height=300)


# --- Recent form ---------------------------------------------------------

st.markdown(section_title("Recent form"), unsafe_allow_html=True)
st.markdown(
    '<p style="color:var(--vlr-text-soft); font-size:0.85rem; margin-top:-0.5rem;">'
    "Last 20 maps, most recent first."
    "</p>",
    unsafe_allow_html=True,
)

if summary["recent_form"].empty:
    st.markdown(
        '<div class="vlr-card" style="color:var(--vlr-text-soft);">No recent form data.</div>',
        unsafe_allow_html=True,
    )
else:
    sparkline_df = summary["recent_form"][["rating"]].reset_index(drop=True).iloc[::-1].reset_index(drop=True)
    st.line_chart(sparkline_df, color=Colors.ACCENT, height=200)

    recent_table = summary["recent_form"].copy()
    recent_table["date"] = recent_table["datetime"].apply(
        lambda x: x.strftime("%b %d") if x is not None else "—"
    )
    recent_table["match"] = recent_table.apply(
        lambda r: f"{r['team_a']} vs {r['team_b']}", axis=1
    )
    display_df = recent_table[["date", "match", "map", "agent", "rating", "acs"]].copy()
    display_df["rating"] = display_df["rating"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
    display_df.columns = ["Date", "Match", "Map", "Agent", "Rating", "ACS"]
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
