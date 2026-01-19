#!/usr/bin/env bash

set -e

echo "Formatting imports with isort..."
python -m isort src/ tests/

echo "Formatting code with black..."
python -m black src/ tests/

echo "Code formatting complete."
