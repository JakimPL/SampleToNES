#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/../lib/root.sh"

PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
VENV_DIR="$PROJECT_DIR/.venv-build"
VENV_PY="$VENV_DIR/bin/python"

EXTRAS=()
for arg in "$@"; do
    case $arg in
        --dev)
            EXTRAS+=("dev")
            ;;
        --gpu)
            EXTRAS+=("gpu")
            ;;
    esac
done

echo "Installing dependencies..."
"$VENV_PY" -m pip install --upgrade pip

if [[ ${#EXTRAS[@]} -gt 0 ]]; then
    EXTRAS_STR=$(IFS=,; echo "${EXTRAS[*]}")
    echo "Installing with extras: $EXTRAS_STR"
    "$VENV_PY" -m pip install ".[$EXTRAS_STR]"
else
    "$VENV_PY" -m pip install .
fi

echo "sampletones Python package installed successfully."
