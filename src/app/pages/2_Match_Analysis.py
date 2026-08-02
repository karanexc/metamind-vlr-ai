"""Match analysis page."""
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
    apply_theme, brand, page_header, section_title, tag, note,
)

st.set_page_config(page_title="Match Analysis — VLR Analytics", page_icon="●", layout="wide")
apply_theme()


st.markdown(brand(), unsafe_allow_html=True)
st.markdown(
    page_header(
        "Match analysis",
        "Pick a completed match. AI-generated breakdown of why one team won, what swung the result, "
        "and which players carried or struggled.",
    ),
    unsafe_allow_html=True,
)


# --- Match selector ------------------------------------------------------

events = data.get_event_options()
event_labels = ["All events"] + [name for _, name in events]

col_event, col_match = st.columns([1, 2])
with col_event:
    event_idx = st.selectbox(
        "Filter by event", range(len(event_labels)),
        format_func=lambda i: event_labels[i],
    )

recent = data.get_recent_matches(limit=200)
if event_idx > 0:
    recent = recent[recent["event"] == event_labels[event_idx]]

if recent.empty:
    st.warning("No matches found for that event.")
    st.stop()


def _label_match(row) -> str:
    date_str = row["datetime"].strftime("%b %d") if row["datetime"] is not None else "?"
    return f"{date_str}  ·  {row['team_a']} {row['score_a']}–{row['score_b']} {row['team_b']}"

recent_labels = [_label_match(r) for _, r in recent.iterrows()]
with col_match:
    match_idx = st.selectbox("Match", range(len(recent_labels)),
                              format_func=lambda i: recent_labels[i])
selected_match_id = int(recent.iloc[match_idx]["match_id"])


detail = data.get_match_detail(selected_match_id)
if detail is None:
    st.error("Could not load match details.")
    st.stop()


# --- Match header hero ---------------------------------------------------

a_won = detail["score_a"] > detail["score_b"]
winner_name = detail["team_a_name"] if a_won else detail["team_b_name"]
loser_name = detail["team_b_name"] if a_won else detail["team_a_name"]

date_str = detail["datetime"].strftime("%B %d, %Y") if detail["datetime"] else ""
patch_str = f" · Patch {detail['patch']}" if detail["patch"] else ""
event_str = detail["event_name"] or "Match"
stage_str = detail["stage"] or ""

st.markdown(
    f'''
    <div class="vlr-hero" style="margin-top:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:1.5rem;">
            <div>
                <div class="vlr-eyebrow">{event_str}</div>
                <div style="color:var(--vlr-text-soft); font-size:0.85rem; margin-top:0.25rem;">{stage_str} · Bo{detail['best_of'] or '?'}{patch_str}</div>
            </div>
            <div style="color:var(--vlr-text-soft); font-size:0.85rem;">{date_str}</div>
        </div>
        <div style="display:flex; align-items:center; justify-content:center; gap:2.5rem;">
            <div style="text-align:right; flex:1;">
                <div style="font-size:1.6rem; font-weight:{700 if a_won else 500}; color:{'var(--vlr-text)' if a_won else 'var(--vlr-text-soft)'}; letter-spacing:-0.015em;">
                    {detail['team_a_name']}
                </div>
            </div>
            <div style="font-family:var(--font-mono); font-size:3rem; font-weight:600; letter-spacing:-0.02em;">
                <span style="color:{'var(--vlr-text)' if a_won else 'var(--vlr-text-soft)'};">{detail['score_a']}</span>
                <span style="color:var(--vlr-text-dim); margin:0 0.4rem;">:</span>
                <span style="color:{'var(--vlr-text)' if not a_won else 'var(--vlr-text-soft)'};">{detail['score_b']}</span>
            </div>
            <div style="text-align:left; flex:1;">
                <div style="font-size:1.6rem; font-weight:{700 if not a_won else 500}; color:{'var(--vlr-text)' if not a_won else 'var(--vlr-text-soft)'}; letter-spacing:-0.015em;">
                    {detail['team_b_name']}
                </div>
            </div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# --- AI analysis section -------------------------------------------------

col_title, col_regen = st.columns([4, 1])
with col_title:
    st.markdown(section_title("AI analysis"), unsafe_allow_html=True)
with col_regen:
    st.markdown('<div style="padding-top:1.85rem;"></div>', unsafe_allow_html=True)
    regenerate = st.button("↻ Regenerate", use_container_width=True, key="regen_btn")

st.markdown(
    f'<p style="color:var(--vlr-text-soft); font-size:0.9rem; margin:-0.5rem 0 1rem 0;">'
    f"Why did {loser_name} drop this match to {winner_name}? "
    f"Grounded in the ML model's feature attribution."
    f"</p>",
    unsafe_allow_html=True,
)

with st.spinner("Generating analysis..." if not regenerate else "Regenerating analysis..."):
    if regenerate:
        analysis = predict.explain_loss_regenerate(
            match_id=selected_match_id,
            team_lost=loser_name,
            team_won=winner_name,
        )
    else:
        analysis = predict.explain_loss(
            match_id=selected_match_id,
            team_lost=loser_name,
            team_won=winner_name,
        )

st.markdown(
    f'<div class="vlr-ai-summary">{analysis.summary}</div>',
    unsafe_allow_html=True,
)


col_factors, col_players = st.columns(2)
with col_factors:
    st.markdown(
        '<div class="vlr-section-title" style="margin-top:1.5rem;">What swung the result</div>',
        unsafe_allow_html=True,
    )
    items_html = "".join([
        f'<div class="vlr-list-item">{f}</div>' for f in analysis.key_factors
    ])
    st.markdown(f'<div class="vlr-list-card">{items_html}</div>', unsafe_allow_html=True)

with col_players:
    st.markdown(
        '<div class="vlr-section-title" style="margin-top:1.5rem;">Standout performances</div>',
        unsafe_allow_html=True,
    )
    up_html = "".join([
        f'<div class="vlr-list-item"><span class="marker-up">▲</span>{p}</div>'
        for p in analysis.standout_players
    ])
    down_html = "".join([
        f'<div class="vlr-list-item"><span class="marker-down">▼</span>{p}</div>'
        for p in analysis.underperformers
    ])
    st.markdown(
        f'<div class="vlr-list-card">{up_html}{down_html}</div>',
        unsafe_allow_html=True,
    )


# --- Per-map breakdown ---------------------------------------------------

st.markdown(section_title("Map-by-map breakdown"), unsafe_allow_html=True)

for game_map in detail["maps"]:
    pick_tag_html = ""
    if game_map["picked_by"]:
        if game_map["picked_by"] == "decider":
            pick_tag_html = tag("Decider")
        else:
            pick_tag_html = tag(f"{game_map['picked_by']} pick")

    st.markdown(
        f'''
        <div style="margin-top:1.5rem; margin-bottom:0.75rem;
                    display:flex; align-items:baseline; gap:0.75rem;">
            <span style="font-size:1.1rem; font-weight:600; color:var(--vlr-text);">
                Map {game_map['index']} · {game_map['name']}
            </span>
            <span style="font-family:var(--font-mono); color:var(--vlr-text-soft); font-weight:500;">
                {game_map['score_a']} – {game_map['score_b']}
            </span>
            {pick_tag_html}
        </div>
        ''',
        unsafe_allow_html=True,
    )

    df_stats = game_map["stats"]
    if df_stats.empty:
        st.markdown(
            '<div class="vlr-card" style="color:var(--vlr-text-soft); font-size:0.85rem;">'
            "No player stats parsed for this map."
            "</div>",
            unsafe_allow_html=True,
        )
        continue

    teams_on_map = df_stats["team"].dropna().unique()
    if len(teams_on_map) >= 2:
        col_t1, col_t2 = st.columns(2)
        for col, team_name in zip([col_t1, col_t2], teams_on_map[:2]):
            with col:
                team_df = df_stats[df_stats["team"] == team_name].copy().drop(columns=["team"])
                team_df["rating"] = team_df["rating"].apply(lambda x: f"{x:.2f}" if x == x and x is not None else "—")
                team_df["adr"] = team_df["adr"].apply(lambda x: f"{x:.0f}" if x == x and x is not None else "—")
                team_df["kast"] = team_df["kast"].apply(lambda x: f"{x:.0f}%" if x == x and x is not None else "—")
                team_df["hs"] = team_df["hs"].apply(lambda x: f"{x:.0f}%" if x == x and x is not None else "—")
                team_df.columns = ["Player", "Agent", "Rating", "ACS", "K", "D", "A", "KAST", "ADR", "HS"]
                st.markdown(
                    f'<div style="font-size:0.85rem; font-weight:600; color:var(--vlr-text); '
                    f'margin-bottom:0.5rem;">{team_name}</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(team_df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df_stats, use_container_width=True, hide_index=True)


st.markdown(
    note(
        "<b>Method</b> &nbsp;·&nbsp; The XGBoost model identifies the most influential "
        "features (via SHAP attribution) for predicting this match outcome. "
        "An LLM (OpenAI) verbalizes those attributions alongside the per-player "
        "stats into the natural-language analysis above. The LLM does not "
        "compute or compare numbers — only the structured presentation is generative."
    ),
    unsafe_allow_html=True,
)
