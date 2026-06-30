#!/usr/bin/env bash
# Launch the Streamlit app.
# Run from the project root: ./scripts/run_app.sh

set -e

# Ensure PYTHONPATH includes src/ so vlr.* imports work
export PYTHONPATH="$(pwd)/src:${PYTHONPATH}"

# Streamlit configuration to suppress its first-run prompts
export STREAMLIT_SERVER_HEADLESS=true
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

streamlit run src/vlr/app/Home.py "$@"
