#!/usr/bin/env bash

set -e

echo "Installing pre-commit hooks..."
python -m pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
echo "Pre-commit hooks installed successfully."
