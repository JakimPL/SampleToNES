#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/scripts/linux/build/python.sh"
source "${SCRIPT_DIR}/scripts/linux/build/venv.sh"
bash "${SCRIPT_DIR}/scripts/linux/build/sampletones.sh" "$@"
bash "${SCRIPT_DIR}/scripts/linux/build/build.sh" "$@"
