# Deploying vlr-analytics (free)

Three free services + a free cron:

| Piece | Host | Free? |
|---|---|---|
| Frontend (Next.js, `web/`) | **Vercel** | yes |
| Postgres | **Neon** | yes (~0.5 GB) |
| Backend (FastAPI + scheduler) | **Render** web service | yes (sleeps when idle) |
| 2-hour refresh | **GitHub Actions** cron (`.github/workflows/refresh.yml`) | yes |

Trade-off of free: after idle the backend cold-starts (~30–60s) and the site
briefly shows sample data until it wakes. A ~$7/mo always-on backend removes that.

---

## 0. Rotate the exposed OpenAI key (do this first)
A real key was committed in `.env.example` on a public repo — treat it as
compromised. Revoke it at platform.openai.com → API keys, create a new one, and
set the new key **only** as a host env var (never in a committed file). It also
lives in git history; rotating makes the leaked one useless.

## 1. Commit the model (once)
`data/` is git-ignored, so the trained model isn't in the repo. Force-add it so
the backend image includes it (otherwise predictions fall back to the stub):
```bash
git add -f data/models/xgboost_v1.pkl
git commit -m "add trained model for deploy"
git push origin main
```

## 2. Neon Postgres
Create a project at neon.tech → copy the connection string → rewrite it as:
```
postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```
That's your `DATABASE_URL`.

## 3. Move your data up (one time)
Your matches/players/VCT/predictions live in the local Docker volume; the cloud
DB starts empty. Dump and restore:
```bash
pg_dump "postgresql://vlr:vlr_dev_password@localhost:5433/vlr" \
  --no-owner --no-privileges > vlr_dump.sql
du -h vlr_dump.sql          # sanity-check it fits Neon's ~0.5 GB free tier
psql "<NEON_URL>" < vlr_dump.sql
```
(If the dump is over ~0.5 GB, trim VCT games or use Supabase's free tier.)

## 4. Backend on Render
- New → **Web Service** → connect this GitHub repo.
- Runtime: **Docker** (uses the repo `Dockerfile`). Instance type: **Free**.
- Environment variables:
  - `DATABASE_URL` = your Neon URL (from step 2)
  - `OPENAI_API_KEY` = your **new** key (or leave unset to disable AI analysis)
  - `LIVE_SCRAPE_ENABLED` = `false`  (cron drives refreshes on free tier)
  - `FRONTEND_URL` = (fill in after step 5)
- Deploy, then note the service URL, e.g. `https://vlr-analytics.onrender.com`.
- Once up, ensure the schema exists (dump already carried it; this is a safety net):
  Render → your service → **Shell** → `python -m src.vlr.cli init-db`

## 5. Frontend on Vercel
- New Project → import this repo → **Root Directory: `web`** (framework auto-detects Next.js).
- Environment variable: `NEXT_PUBLIC_API_URL` = your Render backend URL (step 4).
- Deploy → note the Vercel URL, e.g. `https://vlr-analytics.vercel.app`.

## 6. Close the CORS loop
Back in Render, set `FRONTEND_URL` to your Vercel URL and redeploy the backend
(so the API allows requests from the site).

## 7. Free scheduler (GitHub Actions)
- Repo → Settings → Secrets and variables → Actions → new secret
  `BACKEND_URL` = your Render URL.
- The included `.github/workflows/refresh.yml` pings `/api/v1/live/refresh` every
  2 hours — waking the backend and refreshing the DB. Trigger it once manually
  from the Actions tab to confirm.

## 8. Verify
Open the Vercel link → the site loads. Click **Refresh** → the pill shows
"Refreshing…", the backend scrapes vlr, and the DB grows (persists across
visits). Data only changes on refresh (button or cron); page loads just read.

---

### Caveats (all fine for a demo/dissertation)
- **Cold start**: first visit after idle waits for the backend + Neon to wake;
  sample data shows meanwhile, then flips to real data.
- **Long refresh**: a free host can spin down mid-refresh if no traffic keeps it
  awake; the refresh is idempotent, so the next run continues — nothing corrupts.
- **Model / key**: model must be committed (step 1); never commit the real key.
