#!/usr/bin/env bash
set -e

# --- Check for Python 3.12 or newer ---
PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python version: $PYVER"
MAJOR=$(echo $PYVER | cut -d. -f1)
MINOR=$(echo $PYVER | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 12 ]; }; then
    echo
    echo "ERROR: Python 3.12 or newer is required."
    echo "Please install Python 3.12+ from https://www.python.org/downloads/"
    exit 1
fi

# --- Create venv ---
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# --- Install dependencies ---
echo "Installing dependencies..."
pip install --upgrade pip
pip install .
pip install pyinstaller

# --- Build executable ---
echo "Building executable..."
pyinstaller --name sampletones --onefile --distpath . --icon src/sampletones/icons/icon-256.png --add-data "src/sampletones/icons:sampletones/icons" src/sampletones/__main__.py

echo
if [[ -f sampletones ]]; then
    echo "Build complete: ./sampletones"
else
    echo "Build failed."
fi
