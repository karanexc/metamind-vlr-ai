# VLR Analytics — Implementation Status

**Author:** Karan Mhaswadkar (km14@kent.ac.uk)
**Programme:** MSc Computer Science (AI with Industry Placement), University of Kent
**Supervisor:** Sergey Ovchinnik

This document tracks what has been built, what works, and what remains. Companion to `ARCHITECTURE.md`.

---

## 1. Executive Summary

The system is **feature-complete for the dissertation contribution**. All three gaps identified in the critical review of García-Méndez & de Arriba-Pérez (2025) have been addressed with working code and validated data. Remaining work is deployment, testing, and the dissertation writeup itself.

**Timeline:** 9 iterations completed over ~7 weeks of development.

**Current state:** Full-stack platform running locally, ready for deployment and evaluation.

---

## 2. Iteration History

Each iteration was a self-contained milestone with verification before proceeding.

| Iter. | Scope | Status |
|---|---|---|
| 1 | Project skeleton, Postgres in Docker, SQLAlchemy schema | ✅ Done |
| 2 | HTML scraper — client, parsers, first match ingestion | ✅ Done |
| 3 | Full pipeline — events, matches, maps, veto, player stats | ✅ Done |
| 4 | Bulk scrape of Tier-1 + Challengers 2024–2025 | ✅ Done |
| 5 | Streamlit prototype UI (kept alongside as legacy) | ✅ Done |
| 6 | Feature engineering + baseline evaluation | ✅ Done |
| 7 | XGBoost win prediction model | ✅ Done |
| 7b | Tier-aware features + cross-tier warning UI | ✅ Done |
| 8 | SHAP attribution + GPT-4o explanation layer | ✅ Done |
| 9 (Week 1) | FastAPI backend rebuild | ✅ Done |
| 9 (Week 2) | Next.js 14 frontend with custom design system | ✅ Done |
| 9 (Drop 1) | Live results scheduler + tier filter + regional Players page | ✅ Done |
| 9 (Drop 2) | Player photos + country flags + team logos + bo3-style Teams page | ✅ Done |

---

## 3. Dataset

Scraped from vlr.gg between iterations 1–4, kept current by the live scheduler.

| Entity | Count | Notes |
|---|---|---|
| Matches | 7,248 | Tier-1 + Challengers since 2024 |
| Teams | 1,561 | Classified by region (Americas / EMEA / Pacific / China) |
| Teams with logos | 1,561 | 100% — full backfill completed |
| Players | 7,152 | 7,152 / 7,155 attempted (99.96% success rate) |
| Players with photos + country | 7,152 | Real vlr.gg CDN URLs + ISO-2 country codes |
| Events | 167 | Each classified by tier |
| Maps played | 16,078 | Per-map scores, agent composition |
| Player-map stat rows | 160,284 | Rating, ACS, K/D, KAST, HS%, ADR per player per map |
| Veto actions | 24,551 | Ban/pick history for map-pool analysis |

All IDs are vlr.gg's own IDs, making scrapes fully idempotent.

---

## 4. Features Implemented

### 4.1 Scraping Pipeline (`src/vlr/scraping/`)

- ✅ Rate-limited HTTP client with 2s throttle and exponential backoff
- ✅ Match-listing parser (from `/matches/results` and event pages)
- ✅ Match-detail parser (scores, maps, players, veto, patch, timestamps)
- ✅ Event-listing parser with year filtering
- ✅ Player profile parser (photo, country, real name) — **Drop 2**
- ✅ Team profile parser (logo, country) — **Drop 2**
- ✅ Idempotent inserts (skip already-scraped matches unless `--force`)
- ✅ Resumable backfills (crash halfway → re-run skips completed rows)
- ✅ Background scheduler (`APScheduler`, 30-min interval, configurable via env)

### 4.2 Database (`src/vlr/db/`)

- ✅ 10-table schema (Team, Event, Player, Match, MapPlayed, PlayerMapStat, VetoAction, MatchAnalysisCache, etc.)
- ✅ Custom lightweight migration system (idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS`)
- ✅ 7 migrations applied cleanly across the project (event tier, team region, player photos/countries/real_names, team logos/countries)
- ✅ Full referential integrity (foreign keys, cascade deletes on match)
- ✅ Runs in Docker via `docker-compose`

### 4.3 ML Pipeline (`src/vlr/ml/`)

- ✅ Feature engineering with tier-aware rolling form (win rate, avg rating, ACS trend)
- ✅ Event → tier classifier (`international` / `tier1` / `tier2`)
- ✅ Event → region classifier (`americas` / `emea` / `pacific` / `china`)
- ✅ XGBoost binary classifier trained on 4,000+ decided matches
- ✅ SHAP attribution for feature-level explanation
- ✅ Cross-tier prediction warning (UI signal when out-of-distribution)
- ✅ Trained model persisted to `data/models/xgboost_v1.pkl`

### 4.4 Explanation Layer (`src/vlr/ml/explain.py`)

- ✅ SHAP-ranked features passed to GPT-4o via structured prompt
- ✅ Response schema: `summary`, `key_factors[]`, `standout_players[]`, `underperformers[]`
- ✅ Coaching-analyst voice via system prompt engineering
- ✅ Postgres-backed response cache keyed by `(match_id, model_version)`
- ✅ Cache-first design — re-viewing a match hits Postgres, not OpenAI

### 4.5 Backend API (`src/vlr/api/`)

FastAPI on Uvicorn with Pydantic v2, rate limiting via `slowapi`. Full OpenAPI docs at `/docs`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/stats` | GET | Database size + latest scrape timestamp |
| `/api/v1/matches/recent` | GET | Latest results |
| `/api/v1/matches/by-tier/{tier}` | GET | Filter by international / tier1 / tier2 / all |
| `/api/v1/matches/{id}` | GET | Match detail with maps + players |
| `/api/v1/events` | GET | List events |
| `/api/v1/teams` | GET | List teams with min-match filter |
| `/api/v1/teams/{id}` | GET | Team summary with roster + recent matches |
| `/api/v1/teams/{id}/roster` | GET | Current 5-player roster with photos + flags |
| `/api/v1/regions/{region}/top-teams` | GET | Top 5 teams in a region by recent win rate |
| `/api/v1/regions/{region}/teams-leaderboard` | GET | Full 50-team leaderboard with logos + rosters |
| `/api/v1/players` | GET | List players with min-map filter |
| `/api/v1/players/{id}` | GET | Player summary, form chart, per-agent stats |
| `/api/v1/players/top/{metric}` | GET | Top players by rating / ACS / etc. |
| `/api/v1/predict` | POST | Team A vs B → win probability with SHAP factors |
| `/api/v1/explain/{match_id}` | POST | GPT-4o generated match breakdown |

Background scheduler runs on startup, shuts down cleanly on SIGTERM.

### 4.6 Frontend (`web/`)

Next.js 14 App Router, TypeScript, custom design system.

| Page | Features |
|---|---|
| `/` | Hero with animated stat counters, tool cards with hover states, latest results feed |
| `/predict` | Team A vs Team B selector, animated probability bars, cross-tier warning banner |
| `/match-analysis` | Tier filter → match selector → AI breakdown with regenerate button, per-map summary |
| `/teams` | bo3.gg-style leaderboard: region tabs, search, gold/silver/bronze rank medals, team logos, country flags, roster preview with player photos, expandable row for full details |
| `/players` | Regional team tabs → top-5 team cards with logos → click team → HLTV-style roster with photos + flag overlays → click player → stats + form chart + agent breakdown |

**Design system:**
- Custom Tailwind config with named tokens (`--surface`, `--border`, `--ink-*`, `--accent`)
- Framer Motion for all transitions (fade-in, fade-up, scale-in, animated counters)
- Recharts for player form line-charts
- lucide-react icon set
- Fully responsive (mobile-friendly leaderboard collapses correctly)

### 4.7 CLI Tools (`src/vlr/cli.py`)

Typer + Rich for a polished terminal UX. All commands documented via `--help`.

| Command | Purpose |
|---|---|
| `init-db` | Create schema + apply migrations |
| `scrape-events` | Scrape event listings by year/category |
| `scrape-event <id>` | Scrape all matches in a specific event |
| `scrape-recent` | Backfill recent match results |
| `scrape-recent-results` | Same, wrapped for scheduler use |
| `backfill-tiers` | Classify events into tiers (retroactive) |
| `backfill-regions` | Classify teams into regions from match history |
| `backfill-player-profiles` | Scrape photos + country + real name for all players |
| `backfill-team-logos` | Scrape logo + country for all teams |
| `compute-features` | Compute + cache feature vectors for all matches |
| `train-model` | Train XGBoost on cached features |
| `evaluate-model` | Report accuracy + calibration + confusion matrix |
| `explain-match <id>` | Run SHAP + GPT-4o explanation for a match |
| `show-match <id>` | Print match detail to terminal |
| `show-event <id>` | Print event summary |
| `top-players <metric>` | Print leaderboard by metric |

---

## 5. What Works — Verified

Every item below has been end-to-end tested with real data:

- ✅ Backend serves all endpoints at `http://localhost:8000` with `/docs`
- ✅ Frontend renders all 5 pages at `http://localhost:3000`
- ✅ Live scheduler ticks every 30 min, inserting new match data automatically
- ✅ Player photos load from vlr.gg CDN with country flag overlays (7,152 / 7,155 = 99.96%)
- ✅ Team logos and country flags render on Teams leaderboard (1,561 / 1,561 = 100%)
- ✅ Match Analysis regenerates GPT-4o explanations on demand
- ✅ Prediction endpoint returns calibrated probabilities with tier-aware warnings
- ✅ SHAP attribution matches feature importance rankings
- ✅ Rate limiter prevents abuse of `/explain` (OpenAI cost surface)
- ✅ Response caching bounds OpenAI spend (cache hits are sub-100ms)
- ✅ CORS configured correctly for Next.js frontend → FastAPI backend

---

## 6. What Doesn't Yet Exist

Being explicit about gaps:

- ❌ **No automated tests.** All validation has been manual. Adding `pytest` coverage for the ML pipeline is the highest-priority pre-submission task.
- ❌ **Not deployed.** Runs locally only. Railway (backend + Postgres) + Vercel (frontend) planned but not executed.
- ❌ **No CI/CD.** GitHub Actions not configured. Deferred until tests exist.
- ❌ **No formal evaluation chapter written.** Model performance metrics exist in `evaluate-model` output but haven't been organized into a proper results section.
- ❌ **No user study.** The explanations produced by GPT-4o haven't been evaluated by real coaches or analysts. This is a limitation to acknowledge.
- ❌ **No positional / in-game data.** Riot does not release Valorant demos. Cited as a limitation of the wider ecosystem, not something we chose to skip.
- ❌ **English only.** No multilingual support in the explanation layer.

---

## 7. Deferred / Explicitly Dropped

Decisions made during development, in case supervisor asks:

- **Dark/light theme toggle** — cancelled during Drop 1 planning to focus on shippable features. Documented as an easy post-submission add-on.
- **Country filter on Players page** — cancelled; region grouping was cleaner.
- **Fantasy scoring page** — kept as a stub; would need a scoring rules system beyond dissertation scope.
- **Real-time in-match prediction** — the original scope of the reviewed paper. Not implemented; would require live vlr.gg match feeds and is on the future-work list.

---

## 8. Development Statistics

| Metric | Count |
|---|---|
| Python files | 39 |
| TypeScript / TSX files | 24 |
| Lines of Python (excluding tests) | ~8,500 |
| Lines of TypeScript / TSX | ~3,200 |
| Database migrations applied | 7 |
| API endpoints | 15 |
| Frontend pages | 5 |
| Reusable UI components | 8 (Button, Select, Counter, StatTile, ProbBar, PlayerAvatar, TeamLogo, Nav, Footer) |
| CLI commands | 16 |

---

## 9. What's Next

In recommended order:

1. **Deploy to Railway + Vercel.** Get a live URL for the dissertation and CV. Half a day.
2. **Add pytest coverage** for the ML pipeline (feature determinism, model load, SHAP consistency, tier classifier). One day.
3. **Write the methodology chapter** of the dissertation using this document + `ARCHITECTURE.md` as source material.
4. **Write the results chapter** using output from `evaluate-model` + tier-holdout evaluation.
5. **Write the discussion chapter** covering the three gaps closed, the limitations openly acknowledged, and the future work.

Estimated time to submission-ready draft: 3–4 weeks of consistent writing, starting now.

---

*Last updated: after Drop 2, all backfills verified successful.*
