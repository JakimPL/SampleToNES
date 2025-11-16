#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v flatc >/dev/null 2>&1; then
	echo "flatc not found in PATH. Install the FlatBuffers compiler and retry." >&2
	exit 2
fi

if ! flatc --help 2>&1 | grep -q -- '--python'; then
	echo "flatc does not appear to support Python generation (--python)." >&2
	echo "Please install a flatc binary built with Python support." >&2
	exit 3
fi

echo "Generating Python bindings for all .fbs files in: $SCRIPT_DIR"

while IFS= read -r -d '' f; do
	echo "-> $f"
	flatc --python -o . "$f"
done < <(find . -type f -name '*.fbs' -print0)

echo "Generation finished."
