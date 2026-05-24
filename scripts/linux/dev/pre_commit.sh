#!/usr/bin/env bash

set -e

echo "Installing pre-commit hooks..."
uv run pre-commit install
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
echo "Pre-commit hooks installed successfully."
