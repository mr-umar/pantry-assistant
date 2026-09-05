#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Pantry Assistant server..."
cd "${SCRIPT_DIR}/src"
python3 main.py