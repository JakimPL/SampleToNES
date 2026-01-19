#!/usr/bin/env bash

set -e

if [[ -d ".venv" ]]; then
    echo "Virtual environment already exists. Activating..."
    source .venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Virtual environment created and activated."
fi

return 0
