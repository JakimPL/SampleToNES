#!/usr/bin/env bash

set -e

source "$(dirname "${BASH_SOURCE[0]}")/../lib/root.sh"

if [[ -d ".venv-build" ]]; then
    echo "Virtual environment already exists."
else
    echo "Creating virtual environment..."
    python3 -m venv .venv-build
    echo "Virtual environment created."
fi

return 0
