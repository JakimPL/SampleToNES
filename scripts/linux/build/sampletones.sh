#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/../lib/root.sh"

PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
VENV_DIR="$PROJECT_DIR/.venv-build"
VENV_PY="$VENV_DIR/bin/python"

EXTRAS=("build")
for arg in "$@"; do
    case $arg in
        --gpu)
            EXTRAS+=("gpu")
            ;;
    esac
done

echo "Installing dependencies..."
"$VENV_PY" -m pip install --upgrade pip

EXTRAS_STR=$(IFS=,; echo "${EXTRAS[*]}")
echo "Installing with extras: $EXTRAS_STR"
"$VENV_PY" -m pip install ".[$EXTRAS_STR]"

echo "sampletones Python package installed successfully."
