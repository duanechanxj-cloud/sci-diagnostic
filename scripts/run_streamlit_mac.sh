#!/bin/bash
set -e
cd "$(dirname "$0")/.."
if [ ! -f ".venv/bin/activate" ]; then
  echo "No .venv found. Run scripts/setup_mac.sh first."
  exit 1
fi
source .venv/bin/activate
python -m streamlit run app/streamlit_app.py
