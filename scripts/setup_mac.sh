#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "Primary Science Diagnostic System V2.4.5 - macOS setup"
echo

if [ ! -d ".venv" ]; then
  echo "Creating project virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Setup complete."
echo "Run: scripts/run_streamlit_mac.sh"
