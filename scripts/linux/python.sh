#!/usr/bin/env bash

set -e

PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python version: $PYVER"
MAJOR=$(echo $PYVER | cut -d. -f1)
MINOR=$(echo $PYVER | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 12 ]; }; then
    echo
    echo "ERROR: Python 3.12 or newer is required."
    echo "Please install Python 3.12+ from https://www.python.org/downloads/"
    exit 1
fi
