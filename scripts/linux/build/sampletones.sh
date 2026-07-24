#!/usr/bin/env bash

set -e

source "$(dirname "${BASH_SOURCE[0]}")/../lib/root.sh"

EXTRAS=()
for arg in "$@"; do
    case $arg in
        --dev)
            EXTRAS+=("dev")
            ;;
        --gpu)
            EXTRAS+=("gpu")
            ;;
    esac
done

echo "Installing dependencies..."
pip install --upgrade pip

if [[ ${#EXTRAS[@]} -gt 0 ]]; then
    EXTRAS_STR=$(IFS=,; echo "${EXTRAS[*]}")
    echo "Installing with extras: $EXTRAS_STR"
    pip install ".[$EXTRAS_STR]"
else
    pip install .
fi

echo "sampletones Python package installed successfully."
