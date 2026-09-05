#!/bin/bash
cd "$(dirname "$0")/.."
source .venv/bin/activate
pip freeze > environment_lock.txt
echo "Saved environment_lock.txt"
