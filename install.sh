#!/usr/bin/env bash
set -e

# --- Check for Python 3.12 ---
PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python version: $PYVER"
if [[ $PYVER != 3.12.* ]]; then
    echo
    echo "ERROR: Python 3.12 is required."
    echo "Please install Python 3.12 from https://www.python.org/downloads/"
    exit 1
fi

# --- Create venv ---
python3 -m venv .venv
source .venv/bin/activate

# --- Install dependencies ---
pip install --upgrade pip
pip install .
pip install pyinstaller

# --- Build executable ---
pyinstaller --name sampletones --onefile --distpath . src/sampletones/__main__.py

echo
if [[ -f sampletones ]]; then
    echo "Build complete: ./sampletones"
else
    echo "Build failed."
fi
