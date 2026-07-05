#!/usr/bin/env bash

echo "Removing build artifacts and temporary files..."
rm -rf build/ dist/ *.spec htmlcov/ .coverage
rm -f "./sampletones"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
echo "Cleaned build artifacts and temporary files."
