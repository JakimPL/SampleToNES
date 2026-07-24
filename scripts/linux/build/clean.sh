#!/usr/bin/env bash

source "$(dirname "${BASH_SOURCE[0]}")/../lib/root.sh"

echo "Removing build artifacts and temporary files..."
rm -rf bin/ build/ dist/ *.spec htmlcov/ .coverage
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
echo "Cleaned build artifacts and temporary files."
