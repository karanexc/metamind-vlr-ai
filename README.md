# Valorant Analytics — vlr.gg data pipeline

Iteration 2: now collects **per-player stats** for every map (rating, ACS,
K/D/A, KAST, ADR, HS%, FK/FD, agent played).

## What's new since iteration 1

- New `players` and `player_map_stats` tables
- Parser extracts the per-map stats tables (10 rows per map: 5 per team)
- New `show-match` command — rich per-map breakdown with player stats
- New `top-players` command — leaderboard by average rating/ACS/ADR/etc.
- `stats` command now reports player and player-stat counts

## Migrate from iteration 1

Your existing data is fine. Just add the new tables and re-scrape:

```bash
# 1. Activate venv and set PYTHONPATH (as before)
source .venv/bin/activate
export PYTHONPATH=src

# 2. Create the new tables (init-db is additive — won't touch existing ones)
python -m vlr.cli init-db

# 3. Re-scrape recent results to populate player stats
python -m vlr.cli scrape-recent --pages 1 --verbose

# 4. Sanity-check
python -m vlr.cli stats
```

You should now see non-zero counts for `Players` and `Player-map rows`.

## Quick start (full, from scratch)

```bash
docker compose up -d

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

export PYTHONPATH=src

python -m vlr.cli init-db
python -m vlr.cli scrape-recent --pages 1 --verbose
python -m vlr.cli stats
```

## New commands

### `show-match <id>` — full per-map breakdown

```bash
python -m vlr.cli scrape-matches 670471
python -m vlr.cli show-match 670471
```

You'll get:
- Match header with score, Bo, event, patch
- Per-map: name, score, who picked it
- Per-map: two tables (one per team) with each player's agent, rating, ACS,
  K/D/A, +/-, KAST, ADR, HS% — sorted by rating descending
- Full veto sequence at the bottom

### `top-players` — preview of analytics layer

```bash
python -m vlr.cli top-players --metric rating --min-maps 5 --limit 10
python -m vlr.cli top-players --metric acs --min-maps 10
python -m vlr.cli top-players --metric adr --min-maps 5
```

This is a real (very simple) analytics query: averages a chosen metric across
all maps in your DB, filtered to players with at least `--min-maps` maps.
It's a teaser of the feature-engineering layer we'll build in the next
iteration.

## CLI reference

```bash
python -m vlr.cli init-db                   # create tables (idempotent)
python -m vlr.cli scrape-recent -p 3        # scrape the first 3 results pages
python -m vlr.cli scrape-matches 670471     # scrape specific match id(s)
python -m vlr.cli stats                     # row counts + 5 recent matches
python -m vlr.cli show-match 670471         # full per-map breakdown
python -m vlr.cli top-players               # leaderboard
```

## Schema additions

```
players
  id (vlr.gg player id)  PK
  name
  created_at

player_map_stats
  id                      PK (autoincrement)
  match_id                FK -> matches
  map_id                  FK -> maps_played
  player_id               FK -> players
  team_id                 FK -> teams (nullable)
  team_name               (raw tag from page, e.g. "PRX")
  agent
  rating                  (float, 1.00 = average)
  acs                     (int, Average Combat Score)
  kills, deaths, assists  (int)
  plus_minus              (int, K-D differential)
  kast                    (int, percentage)
  adr                     (float, Average Damage per Round)
  hs_pct                  (int, percentage)
  fk, fd, fk_fd_diff      (int)
  UNIQUE (map_id, player_id)
```

## Useful SQL queries

```sql
-- Top 10 players by average rating, min 5 maps
SELECT p.name,
       COUNT(*) AS maps,
       ROUND(AVG(pms.rating)::numeric, 2) AS avg_rating,
       ROUND(AVG(pms.acs)::numeric, 0) AS avg_acs
FROM player_map_stats pms
JOIN players p ON p.id = pms.player_id
WHERE pms.rating IS NOT NULL
GROUP BY p.id, p.name
HAVING COUNT(*) >= 5
ORDER BY avg_rating DESC
LIMIT 10;

-- Per-agent win rate (rough — needs to be joined to map outcomes for true wr)
SELECT agent, COUNT(*) AS times_played
FROM player_map_stats
WHERE agent IS NOT NULL
GROUP BY agent
ORDER BY times_played DESC;

-- Per-map agent popularity
SELECT mp.map_name, pms.agent, COUNT(*) AS picks
FROM player_map_stats pms
JOIN maps_played mp ON mp.id = pms.map_id
WHERE pms.agent IS NOT NULL
GROUP BY mp.map_name, pms.agent
ORDER BY mp.map_name, picks DESC;

-- A specific player's recent performances
SELECT m.match_datetime, m.team_a_name, m.team_b_name, mp.map_name,
       pms.agent, pms.rating, pms.acs, pms.kills, pms.deaths
FROM player_map_stats pms
JOIN matches m ON m.id = pms.match_id
JOIN maps_played mp ON mp.id = pms.map_id
JOIN players p ON p.id = pms.player_id
WHERE p.name = 'aspas'
ORDER BY m.scraped_at DESC
LIMIT 20;
```

## When the player-stats parser breaks

The risk surface is now bigger — per-player tables have more selectors than
match-header fields. If `show-match` reports "(no player stats parsed)" or
fields come back as `-`, here's the debug flow:

1. Pick a match where stats look wrong
2. Re-scrape that match with verbose output:
   `python -m vlr.cli scrape-matches <id> -v`
3. Save the raw HTML for inspection:
   `curl -A "vlr-analytics" https://www.vlr.gg/<id>/_ > /tmp/m.html`
4. Look at the actual class names being used:
   `grep -oE 'class="[^"]*(?:mod-overview|vm-stats|wf-table-inset|side mod-both)[^"]*"' /tmp/m.html | sort -u`
5. Edit the relevant selector in `src/vlr/scraping/parsers.py`. The three
   places likely to need updates are: `_extract_player_stats` (table class
   pattern), `_parse_player_row` (player/agent cell selectors), and
   `_extract_cell_value` (the 'both' value detector).

## What this does NOT do yet

- Round-by-round outcomes and economy data
- Incremental scraping that stops at the oldest match already in DB
- Feature engineering (player–agent–map aggregates, time-decayed form)
- Models (logistic baseline, XGBoost, two-tower)

Those come in iteration 3.

## Project layout

```
src/vlr/
  config.py
  db/
    models.py       # 7 tables: Team, Event, Match, MapPlayed, VetoAction, Player, PlayerMapStat
    session.py
  scraping/
    client.py
    parsers.py      # the one file to edit when HTML changes
    pipeline.py
  cli.py
docker-compose.yml
requirements.txt
```
