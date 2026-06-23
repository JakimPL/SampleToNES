#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

EXTRAS=""
GPU=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            if [[ -n "$EXTRAS" ]]; then
                EXTRAS="${EXTRAS},dev"
            else
                EXTRAS="dev"
            fi
            ;;
        --gpu)
            GPU=true
            if [[ -n "$EXTRAS" ]]; then
                EXTRAS="${EXTRAS},gpu"
            else
                EXTRAS="gpu"
            fi
            ;;
    esac
    shift
done

if [[ "$GPU" == "true" ]]; then
    bash "${SCRIPT_DIR}/cuda.sh"
fi

echo "Installing dependencies..."
pip install --upgrade pip

if [[ -n "$EXTRAS" ]]; then
    echo "Installing with extras: $EXTRAS"
    pip install ".[${EXTRAS}]"
else
    pip install .
fi

echo "sampletones Python package installed successfully."
exit 0
