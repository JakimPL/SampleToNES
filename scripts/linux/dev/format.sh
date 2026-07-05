#!/usr/bin/env bash

set -e

echo "Formatting imports with isort..."
uv run python -m isort src/ tests/

echo "Formatting code with black..."
uv run python -m black src/ tests/

echo "Code formatting complete."
