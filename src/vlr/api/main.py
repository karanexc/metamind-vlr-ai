"""FastAPI app — JSON API over the vlr-analytics pipeline.

Run with:
    python -m uvicorn vlr.api.main:app --reload --port 8000

Then visit http://localhost:8000/docs for interactive API docs.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .limits import limiter
from .routes import abilities, depth, explain, live, matches, meta, pickem, players, predict, predictions, stats, teams
from .scheduler import start_scheduler, stop_scheduler

log = logging.getLogger(__name__)


# --- App ------------------------------------------------------------------

app = FastAPI(
    title="VLR Analytics API",
    description=(
        "JSON API for Valorant esports analytics. Backs a Next.js frontend "
        "with match prediction, player/team stats, and LLM-generated analysis."
    ),
    version="1.0.0",
)


@app.on_event("startup")
async def _startup():
    start_scheduler()


@app.on_event("shutdown")
async def _shutdown():
    stop_scheduler()


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- CORS — allow the Next.js frontend ------------------------------------
# In development the Next.js dev server runs on localhost:3000. In production
# it'll be a Vercel URL. We allow both, plus any URL set via FRONTEND_URL env.

_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend := os.environ.get("FRONTEND_URL"):
    _allowed_origins.append(frontend)
# In production also allow any *.vercel.app subdomain (so preview deploys work)
_allow_origin_regex = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --- Health check ---------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Used by Railway / monitoring to verify the API is alive."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    """Quick orientation for someone hitting the bare URL."""
    return {
        "name": "VLR Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "stats": "/api/v1/stats",
            "teams": "/api/v1/teams",
            "players": "/api/v1/players",
            "matches": "/api/v1/matches/recent",
            "predict": "POST /api/v1/predict",
            "explain": "/api/v1/explain/{match_id}",
        },
    }


# --- Routes --------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(stats.router, prefix=API_PREFIX, tags=["stats"])
app.include_router(teams.router, prefix=API_PREFIX, tags=["teams"])
app.include_router(players.router, prefix=API_PREFIX, tags=["players"])
app.include_router(matches.router, prefix=API_PREFIX, tags=["matches"])
app.include_router(predict.router, prefix=API_PREFIX, tags=["predict"])
app.include_router(explain.router, prefix=API_PREFIX, tags=["explain"])
app.include_router(pickem.router, prefix=API_PREFIX, tags=["pickem"])
app.include_router(live.router, prefix=API_PREFIX, tags=["live"])
app.include_router(meta.router, prefix=API_PREFIX, tags=["meta"])
app.include_router(depth.router, prefix=API_PREFIX, tags=["depth"])
app.include_router(abilities.router, prefix=API_PREFIX, tags=["abilities"])
app.include_router(predictions.router, prefix=API_PREFIX, tags=["predictions"])


# --- Generic error handler ------------------------------------------------


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so the API never returns an HTML stacktrace."""
    log.exception("Unhandled exception in %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
