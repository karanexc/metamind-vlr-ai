"""Theme module for VLR Analytics.

Design language: dark, modern AI-product aesthetic. Inspired by oxlo.ai but
toned down for a coaching dashboard. Inter for sans-serif, JetBrains Mono
for numbers. Off-black surfaces, subtle borders, sparing red accent.
"""
from __future__ import annotations

import streamlit as st


# --- Color tokens ---------------------------------------------------------

class Colors:
    BG = "#0A0A0B"
    SURFACE = "#131316"
    SURFACE_HOVER = "#181820"
    SURFACE_HIGH = "#1C1C22"
    BORDER = "#222228"
    BORDER_HOVER = "#33333D"
    BORDER_ACCENT = "#FA4454"

    TEXT = "#F5F5F7"
    TEXT_SOFT = "#9CA3AF"
    TEXT_DIM = "#5A5A63"

    ACCENT = "#FA4454"
    ACCENT_HOVER = "#FF5C6B"
    ACCENT_BG = "rgba(250, 68, 84, 0.10)"

    SUCCESS = "#22C55E"
    SUCCESS_BG = "rgba(34, 197, 94, 0.10)"
    WARNING = "#F59E0B"
    WARNING_BG = "rgba(245, 158, 11, 0.10)"


# --- Global CSS -----------------------------------------------------------

_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Color system as CSS variables for reuse */
:root, .stApp {
    --vlr-bg: #0A0A0B;
    --vlr-surface: #131316;
    --vlr-surface-hover: #181820;
    --vlr-surface-high: #1C1C22;
    --vlr-border: #222228;
    --vlr-border-hover: #33333D;
    --vlr-text: #F5F5F7;
    --vlr-text-soft: #9CA3AF;
    --vlr-text-dim: #5A5A63;
    --vlr-accent: #FA4454;
    --vlr-accent-hover: #FF5C6B;
    --vlr-accent-bg: rgba(250, 68, 84, 0.10);
    --vlr-success: #22C55E;
    --vlr-warning: #F59E0B;

    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', Menlo, monospace;
}

/* Base reset */
html, body, .stApp {
    background: var(--vlr-bg) !important;
    color: var(--vlr-text) !important;
    font-family: var(--font-sans) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Hide Streamlit chrome */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
.stDeployButton { display: none !important; }

/* Main content padding */
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 5rem !important;
    max-width: 1240px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--vlr-bg) !important;
    border-right: 1px solid var(--vlr-border) !important;
}
section[data-testid="stSidebar"] > div {
    padding-top: 1.5rem !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
    padding-top: 0.5rem;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul {
    padding-top: 0;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    color: var(--vlr-text-soft) !important;
    font-family: var(--font-sans) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1rem !important;
    border-radius: 6px !important;
    transition: all 0.12s ease !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
    background: var(--vlr-surface) !important;
    color: var(--vlr-text) !important;
}

/* Typography */
h1 {
    font-family: var(--font-sans) !important;
    font-weight: 700 !important;
    font-size: 2.25rem !important;
    letter-spacing: -0.025em !important;
    color: var(--vlr-text) !important;
    margin: 0 !important;
    line-height: 1.15 !important;
}
h2 {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.015em !important;
    color: var(--vlr-text) !important;
    margin-top: 2.5rem !important;
    margin-bottom: 1rem !important;
}
h3 {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 1.125rem !important;
    color: var(--vlr-text) !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
}
p, label, span, div {
    font-family: var(--font-sans);
}

/* HR */
hr {
    border: none !important;
    border-top: 1px solid var(--vlr-border) !important;
    margin: 2rem 0 !important;
}

/* Buttons */
.stButton button {
    background: var(--vlr-surface) !important;
    border: 1px solid var(--vlr-border) !important;
    color: var(--vlr-text) !important;
    border-radius: 8px !important;
    font-family: var(--font-sans) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.55rem 1.1rem !important;
    transition: all 0.12s ease !important;
}
.stButton button:hover {
    background: var(--vlr-surface-hover) !important;
    border-color: var(--vlr-border-hover) !important;
    color: var(--vlr-text) !important;
}
.stButton button[kind="primary"],
.stButton button[data-testid="baseButton-primary"] {
    background: var(--vlr-accent) !important;
    border-color: var(--vlr-accent) !important;
    color: white !important;
}
.stButton button[kind="primary"]:hover,
.stButton button[data-testid="baseButton-primary"]:hover {
    background: var(--vlr-accent-hover) !important;
    border-color: var(--vlr-accent-hover) !important;
}

/* Selectbox + multiselect */
.stSelectbox label, .stMultiSelect label, .stRadio label {
    font-family: var(--font-sans) !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    color: var(--vlr-text-soft) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

[data-baseweb="select"] > div {
    background: var(--vlr-surface) !important;
    border: 1px solid var(--vlr-border) !important;
    border-radius: 8px !important;
    color: var(--vlr-text) !important;
    font-family: var(--font-sans) !important;
}
[data-baseweb="select"] > div:hover {
    border-color: var(--vlr-border-hover) !important;
}
[data-baseweb="popover"] {
    background: var(--vlr-surface-high) !important;
    border: 1px solid var(--vlr-border) !important;
    border-radius: 8px !important;
}
[data-baseweb="menu"] {
    background: var(--vlr-surface-high) !important;
}
[data-baseweb="menu"] li {
    color: var(--vlr-text) !important;
    font-family: var(--font-sans) !important;
}
[data-baseweb="menu"] li:hover {
    background: var(--vlr-surface-hover) !important;
}

/* Multiselect chips */
[data-baseweb="tag"] {
    background: var(--vlr-accent-bg) !important;
    border: 1px solid var(--vlr-accent) !important;
    color: var(--vlr-accent) !important;
    border-radius: 6px !important;
    font-family: var(--font-sans) !important;
}

/* Radio */
.stRadio [role="radiogroup"] label {
    color: var(--vlr-text-soft) !important;
}
.stRadio [role="radio"][aria-checked="true"] + div {
    color: var(--vlr-text) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--vlr-border) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--vlr-text-soft) !important;
    font-family: var(--font-sans) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.75rem 1.25rem !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    margin-bottom: -1px !important;
}
.stTabs [aria-selected="true"] {
    color: var(--vlr-text) !important;
    border-bottom: 2px solid var(--vlr-accent) !important;
}

/* DataFrame styling */
.stDataFrame {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid var(--vlr-border) !important;
}
.stDataFrame [data-testid="stDataFrameResizable"] {
    background: var(--vlr-surface) !important;
}

/* Charts */
.stPlotlyChart, [data-testid="stPlotlyChart"] {
    background: var(--vlr-surface) !important;
    border: 1px solid var(--vlr-border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

/* Hide the default vega-lite tooltip overlap */
.stVegaLiteChart, [data-testid="stVegaLiteChart"] {
    background: var(--vlr-surface) !important;
    border: 1px solid var(--vlr-border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

/* Custom utility classes ---------------------------------------------- */

.vlr-tag {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    font-size: 0.7rem;
    font-family: var(--font-sans);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--vlr-text-soft);
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 6px;
}
.vlr-tag-accent {
    color: var(--vlr-accent);
    background: var(--vlr-accent-bg);
    border-color: var(--vlr-accent);
}

.vlr-mono {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}

.vlr-eyebrow {
    font-size: 0.72rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--vlr-text-dim);
}

.vlr-page-title {
    font-family: var(--font-sans);
    font-weight: 700;
    font-size: 2.5rem;
    letter-spacing: -0.025em;
    color: var(--vlr-text);
    margin: 0 0 0.5rem 0;
    line-height: 1.1;
}
.vlr-page-subtitle {
    color: var(--vlr-text-soft);
    font-size: 1rem;
    margin: 0 0 2rem 0;
    max-width: 720px;
    line-height: 1.55;
}

.vlr-section-title {
    font-family: var(--font-sans);
    font-weight: 600;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--vlr-text-soft);
    margin: 2rem 0 1rem 0;
}

.vlr-card {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    transition: border-color 0.12s ease;
}
.vlr-card:hover {
    border-color: var(--vlr-border-hover);
}
.vlr-card-accent {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-left: 3px solid var(--vlr-accent);
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
}

.vlr-stat {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    transition: border-color 0.12s ease;
}
.vlr-stat:hover { border-color: var(--vlr-border-hover); }
.vlr-stat-label {
    font-size: 0.72rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--vlr-text-dim);
    margin-bottom: 0.6rem;
}
.vlr-stat-value {
    font-family: var(--font-sans);
    font-size: 2rem;
    font-weight: 700;
    color: var(--vlr-text);
    line-height: 1;
    letter-spacing: -0.02em;
}
.vlr-stat-value.mono {
    font-family: var(--font-mono);
    font-weight: 600;
}
.vlr-stat-sub {
    font-size: 0.78rem;
    color: var(--vlr-text-soft);
    margin-top: 0.55rem;
}

.vlr-nav-card {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 14px;
    padding: 1.5rem;
    transition: all 0.15s ease;
    height: 100%;
    cursor: pointer;
}
.vlr-nav-card:hover {
    border-color: var(--vlr-accent);
    transform: translateY(-2px);
}
.vlr-nav-card-icon {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: var(--vlr-accent-bg);
    color: var(--vlr-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    margin-bottom: 1rem;
    font-family: var(--font-sans);
}
.vlr-nav-card h3 {
    margin: 0 0 0.5rem 0 !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
}
.vlr-nav-card p {
    color: var(--vlr-text-soft);
    font-size: 0.875rem;
    line-height: 1.5;
    margin: 0;
}

/* Big prediction hero */
.vlr-hero {
    background: linear-gradient(180deg, var(--vlr-surface) 0%, var(--vlr-surface-high) 100%);
    border: 1px solid var(--vlr-border);
    border-radius: 16px;
    padding: 2rem 2.25rem;
    margin: 1rem 0;
}

.vlr-hero-teams {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
}
.vlr-hero-team {
    flex: 1;
    min-width: 0;
}
.vlr-hero-team.right { text-align: right; }
.vlr-hero-team-label {
    font-size: 0.7rem;
    color: var(--vlr-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
}
.vlr-hero-team-name {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--vlr-text);
    letter-spacing: -0.015em;
}
.vlr-hero-meta {
    font-size: 0.78rem;
    color: var(--vlr-text-soft);
    padding: 0.35rem 0.75rem;
    background: var(--vlr-bg);
    border-radius: 9999px;
    border: 1px solid var(--vlr-border);
}

.vlr-hero-probs {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
}
.vlr-hero-prob {
    font-family: var(--font-mono);
    font-size: 2.5rem;
    font-weight: 600;
    line-height: 1;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
}
.vlr-hero-prob.winner { color: var(--vlr-text); }
.vlr-hero-prob.loser { color: var(--vlr-text-dim); }

.vlr-probbar {
    flex: 1;
    height: 6px;
    background: var(--vlr-bg);
    border-radius: 9999px;
    overflow: hidden;
    border: 1px solid var(--vlr-border);
}
.vlr-probbar-fill {
    height: 100%;
    background: var(--vlr-accent);
    transition: width 0.5s ease;
}

.vlr-hero-footer {
    text-align: center;
    color: var(--vlr-text-soft);
    font-size: 0.85rem;
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid var(--vlr-border);
}
.vlr-hero-footer b { color: var(--vlr-text); font-family: var(--font-mono); font-weight: 600; }

/* Map prediction grid card */
.vlr-mapcard {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    transition: border-color 0.12s ease;
}
.vlr-mapcard:hover { border-color: var(--vlr-border-hover); }
.vlr-mapcard-name {
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 0.6rem;
    color: var(--vlr-text);
}
.vlr-mapcard-probs {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.5rem;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}
.vlr-mapcard-probs .winner { color: var(--vlr-text); font-weight: 600; }
.vlr-mapcard-probs .loser { color: var(--vlr-text-dim); }
.vlr-mapcard-bar {
    height: 4px;
    background: var(--vlr-bg);
    border-radius: 9999px;
    overflow: hidden;
    margin-bottom: 0.6rem;
    border: 1px solid var(--vlr-border);
}
.vlr-mapcard-conf {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.vlr-mapcard-conf.high { color: var(--vlr-success); }
.vlr-mapcard-conf.medium { color: var(--vlr-warning); }
.vlr-mapcard-conf.low { color: var(--vlr-text-dim); }

/* Match row */
.vlr-match {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.85rem 1.25rem;
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 10px;
    margin-bottom: 0.5rem;
    transition: border-color 0.12s ease;
}
.vlr-match:hover { border-color: var(--vlr-border-hover); }
.vlr-match-result {
    width: 32px; height: 32px;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; color: white;
    font-family: var(--font-mono);
    font-size: 0.85rem;
}
.vlr-match-result.win { background: var(--vlr-success); }
.vlr-match-result.loss { background: var(--vlr-accent); }
.vlr-match-meta {
    font-size: 0.72rem;
    color: var(--vlr-text-dim);
    margin-bottom: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.vlr-match-teams {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.95rem;
}
.vlr-match-teams .score {
    font-family: var(--font-mono);
    font-weight: 600;
    color: var(--vlr-text);
    padding: 0 0.5rem;
}
.vlr-match-bo {
    font-size: 0.72rem;
    color: var(--vlr-text-dim);
    font-family: var(--font-mono);
}

/* Inline note callout */
.vlr-note {
    background: var(--vlr-warning) ;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-left: 3px solid var(--vlr-warning);
    border-radius: 8px;
    padding: 0.85rem 1.1rem;
    margin-top: 2rem;
    font-size: 0.85rem;
    color: var(--vlr-text-soft);
}
.vlr-note b { color: var(--vlr-warning); font-weight: 600; }

/* Roster card (player tile in team page) */
.vlr-roster-card {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    height: 100%;
    transition: border-color 0.12s ease;
}
.vlr-roster-card:hover { border-color: var(--vlr-border-hover); }
.vlr-roster-card-label {
    font-size: 0.65rem;
    color: var(--vlr-text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.vlr-roster-card-name {
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 0.4rem;
    color: var(--vlr-text);
}

/* AI analysis card variant */
.vlr-ai-summary {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-left: 3px solid var(--vlr-accent);
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    font-size: 0.95rem;
    line-height: 1.65;
    color: var(--vlr-text);
}

.vlr-list-card {
    background: var(--vlr-surface);
    border: 1px solid var(--vlr-border);
    border-radius: 10px;
    padding: 0.5rem 1.25rem;
}
.vlr-list-item {
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--vlr-border);
    font-size: 0.9rem;
    color: var(--vlr-text);
}
.vlr-list-item:last-child { border-bottom: none; }
.vlr-list-item .marker-up { color: var(--vlr-success); margin-right: 0.5rem; }
.vlr-list-item .marker-down { color: var(--vlr-accent); margin-right: 0.5rem; }

/* Brand header (top of every page) */
.vlr-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--vlr-text);
    margin-bottom: 2rem;
}
.vlr-brand-dot {
    width: 9px; height: 9px;
    background: var(--vlr-accent);
    border-radius: 50%;
}
</style>
"""


def apply_theme() -> None:
    """Inject the full stylesheet. Call once at the top of every page."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# --- Reusable HTML helpers -----------------------------------------------


def brand() -> str:
    return (
        '<div class="vlr-brand">'
        '<span class="vlr-brand-dot"></span>'
        'VLR Analytics'
        '</div>'
    )


def page_header(title: str, subtitle: str = "") -> str:
    sub_html = f'<p class="vlr-page-subtitle">{subtitle}</p>' if subtitle else ""
    return f'<h1 class="vlr-page-title">{title}</h1>{sub_html}'


def section_title(label: str) -> str:
    return f'<div class="vlr-section-title">{label}</div>'


def stat_tile(label: str, value: str, sub: str = "", mono: bool = False) -> str:
    mono_cls = " mono" if mono else ""
    sub_html = f'<div class="vlr-stat-sub">{sub}</div>' if sub else ""
    return f'''
    <div class="vlr-stat">
        <div class="vlr-stat-label">{label}</div>
        <div class="vlr-stat-value{mono_cls}">{value}</div>
        {sub_html}
    </div>'''


def nav_card(icon: str, title: str, body: str) -> str:
    return f'''
    <div class="vlr-nav-card">
        <div class="vlr-nav-card-icon">{icon}</div>
        <h3>{title}</h3>
        <p>{body}</p>
    </div>'''


def tag(text: str, accent: bool = False) -> str:
    cls = "vlr-tag-accent" if accent else "vlr-tag"
    return f'<span class="vlr-tag {cls}">{text}</span>'


def note(body: str) -> str:
    return f'<div class="vlr-note">{body}</div>'


def prediction_hero(
    team_a: str, team_b: str,
    prob_a: float, prob_b: float,
    score_a: int, score_b: int,
    best_of: int, confidence: str,
    event: str = "",
) -> str:
    """Big hero card with the headline prediction."""
    prob_a_pct = round(prob_a * 100)
    prob_b_pct = round(prob_b * 100)
    a_wins = prob_a >= prob_b
    a_cls = "winner" if a_wins else "loser"
    b_cls = "loser" if a_wins else "winner"
    a_team_color = "var(--vlr-text)" if a_wins else "var(--vlr-text-soft)"
    b_team_color = "var(--vlr-text)" if not a_wins else "var(--vlr-text-soft)"

    meta_html = f'<div class="vlr-hero-meta">{event} · Bo{best_of}</div>' if event else f'<div class="vlr-hero-meta">Bo{best_of}</div>'

    return f'''
    <div class="vlr-hero">
        <div class="vlr-hero-teams">
            <div class="vlr-hero-team">
                <div class="vlr-hero-team-label">Team A</div>
                <div class="vlr-hero-team-name" style="color:{a_team_color};">{team_a}</div>
            </div>
            {meta_html}
            <div class="vlr-hero-team right">
                <div class="vlr-hero-team-label">Team B</div>
                <div class="vlr-hero-team-name" style="color:{b_team_color};">{team_b}</div>
            </div>
        </div>
        <div class="vlr-hero-probs">
            <div class="vlr-hero-prob {a_cls}">{prob_a_pct}%</div>
            <div class="vlr-probbar">
                <div class="vlr-probbar-fill" style="width:{prob_a_pct}%;"></div>
            </div>
            <div class="vlr-hero-prob {b_cls}">{prob_b_pct}%</div>
        </div>
        <div class="vlr-hero-footer">
            Projected scoreline <b>{score_a} – {score_b}</b>
            &nbsp;·&nbsp; Confidence <b style="font-family:var(--font-sans); text-transform:uppercase; letter-spacing:0.05em; font-size:0.8em;">{confidence}</b>
        </div>
    </div>'''


def map_prediction_card(name: str, prob_a: float, prob_b: float, confidence: str) -> str:
    pa = round(prob_a * 100)
    pb = round(prob_b * 100)
    a_wins = prob_a >= prob_b
    a_cls = "winner" if a_wins else "loser"
    b_cls = "loser" if a_wins else "winner"
    return f'''
    <div class="vlr-mapcard">
        <div class="vlr-mapcard-name">{name}</div>
        <div class="vlr-mapcard-probs">
            <span class="{a_cls}">{pa}%</span>
            <span class="{b_cls}">{pb}%</span>
        </div>
        <div class="vlr-mapcard-bar">
            <div class="vlr-probbar-fill" style="width:{pa}%;"></div>
        </div>
        <div class="vlr-mapcard-conf {confidence}">{confidence} confidence</div>
    </div>'''


def match_row(
    team_a: str, score_a: int, team_b: str, score_b: int,
    event: str, date: str, best_of: int = None,
    perspective_team: str = None,
) -> str:
    """Render a compact match row. If perspective_team given, show W/L badge."""
    parts = []
    if perspective_team:
        is_team_a = team_a == perspective_team
        own = score_a if is_team_a else score_b
        opp = score_b if is_team_a else score_a
        won = own > opp
        opp_name = team_b if is_team_a else team_a
        badge_cls = "win" if won else "loss"
        badge_text = "W" if won else "L"

        meta_pieces = [event or "—", date or "—"]
        if best_of:
            meta_pieces.append(f"Bo{best_of}")
        meta = " · ".join(meta_pieces)

        parts.append(f'<div class="vlr-match-result {badge_cls}">{badge_text}</div>')
        parts.append(f'''<div style="flex:1;">
            <div class="vlr-match-meta">{meta}</div>
            <div class="vlr-match-teams">
                vs <b>{opp_name}</b>
                <span class="score">{own} – {opp}</span>
            </div>
        </div>''')
    else:
        winner_a = score_a > score_b
        a_style = "color: var(--vlr-text); font-weight:600;" if winner_a else "color: var(--vlr-text-soft);"
        b_style = "color: var(--vlr-text); font-weight:600;" if not winner_a else "color: var(--vlr-text-soft);"

        meta = f"{event or '—'} · {date or '—'}"
        bo_html = f'<div class="vlr-match-bo">Bo{best_of}</div>' if best_of else ""

        parts.append(f'''<div style="flex:1;">
            <div class="vlr-match-meta">{meta}</div>
            <div class="vlr-match-teams">
                <span style="{a_style}">{team_a}</span>
                <span class="score">{score_a} : {score_b}</span>
                <span style="{b_style}">{team_b}</span>
            </div>
        </div>''')
        parts.append(bo_html)

    return f'<div class="vlr-match">{"".join(parts)}</div>'
