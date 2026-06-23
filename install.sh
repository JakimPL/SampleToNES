#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NO_VENV=false
GPU=false
PASS_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --no-venv)
            NO_VENV=true
            ;;
        --gpu)
            GPU=true
            PASS_ARGS+=("$arg")
            ;;
        *)
            PASS_ARGS+=("$arg")
            ;;
    esac
done

if [[ "$NO_VENV" == "false" ]]; then
    source "${SCRIPT_DIR}/scripts/linux/build/python.sh"
    source "${SCRIPT_DIR}/scripts/linux/build/venv.sh"
fi

source "${SCRIPT_DIR}/scripts/linux/build/dependencies.sh"
if [[ "$GPU" == "true" ]]; then
    bash "${SCRIPT_DIR}/scripts/linux/build/cuda.sh"
fi
bash "${SCRIPT_DIR}/scripts/linux/build/sampletones.sh" "${PASS_ARGS[@]}"
bash "${SCRIPT_DIR}/scripts/linux/build/build.sh"
