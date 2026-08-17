#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/../lib/root.sh"

PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
VENV_PY="$PROJECT_DIR/.venv-build/bin/python"

echo "Generating the icon suite..."
"$VENV_PY" scripts/assets/icons.py
