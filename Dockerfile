# Backend image for the FastAPI API + in-process scheduler.
# Used by Render / Fly / Railway. The frontend (web/) deploys separately on Vercel.
FROM python:3.12-slim

# Build deps for lxml (scraper) + psycopg. Removed after install to keep it lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Whole repo, incl. the model file (force-add it first — see DEPLOY.md — since
# data/ is git-ignored, otherwise predictions fall back to the stub).
COPY . .

ENV PYTHONPATH=/app/src
ENV PORT=8000

# $PORT is provided by the host (Render/Fly). The scheduler runs in-process;
# on free hosts that sleep, set LIVE_SCRAPE_ENABLED=false and drive refreshes
# with the GitHub Actions cron in .github/workflows/refresh.yml.
CMD ["sh", "-c", "uvicorn vlr.api.main:app --host 0.0.0.0 --port ${PORT}"]
