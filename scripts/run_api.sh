#!/usr/bin/env bash
# Launch the FastAPI dev server.
set -e
export PYTHONPATH="$(pwd)/src:${PYTHONPATH}"
uvicorn vlr.api.main:app --reload --port 8000 "$@"
