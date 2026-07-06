#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NO_VENV=false
PASS_ARGS=()

for arg in "$@"; do
    if [[ "$arg" == "--no-venv" ]]; then
        NO_VENV=true
    else
        PASS_ARGS+=("$arg")
    fi
done

if [[ "$NO_VENV" == "false" ]]; then
    source "${SCRIPT_DIR}/scripts/linux/build/python.sh"
    source "${SCRIPT_DIR}/scripts/linux/build/venv.sh"
fi

source "${SCRIPT_DIR}/scripts/linux/build/dependencies.sh"
bash "${SCRIPT_DIR}/scripts/linux/build/sampletones.sh" "${PASS_ARGS[@]}"
bash "${SCRIPT_DIR}/scripts/linux/build/build.sh" "${PASS_ARGS[@]}"
