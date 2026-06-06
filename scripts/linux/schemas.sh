#!/usr/bin/env bash

set -euo pipefail

START_DIR="$(pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMAS_DIR="$(cd "$SCRIPT_DIR/../../src/sampletones_schemas" && pwd)"
cd "$SCHEMAS_DIR"

if ! command -v flatc >/dev/null 2>&1; then
	echo "flatc not found in PATH. Install the FlatBuffers compiler and retry." >&2
	exit 2
fi

if ! flatc --help 2>&1 | grep -q -- '--python'; then
	echo "flatc does not appear to support Python generation (--python)." >&2
	echo "Please install a flatc binary built with Python support." >&2
	exit 3
fi

echo "Removing existing .py files under ${SCHEMAS_DIR}..."
find "$SCHEMAS_DIR" -type f -name '*.py' -print0 | xargs -0 rm -f -- || true

DEFINITIONS_DIR="$SCHEMAS_DIR/definitions"
echo "Generating Python bindings for all .fbs files in: ${DEFINITIONS_DIR}..."
TARGET_DIR="$SCHEMAS_DIR/.."
mapfile -t FBS_FILES < <(find "$DEFINITIONS_DIR" -type f -name '*.fbs' | sort)
if [ "${#FBS_FILES[@]}" -eq 0 ]; then
# echo filename path
  echo "no .fbs files found" >&2
  exit 0
fi
echo "Found ${#FBS_FILES[@]} .fbs files."
flatc --python -I "$DEFINITIONS_DIR" -o "$TARGET_DIR" "${FBS_FILES[@]}"

echo "Running pre-commit on generated files..."
pre-commit run black --files $(find "$TARGET_DIR" -type f -name '*.py' -print0 | xargs -0)

echo "Generation finished."
