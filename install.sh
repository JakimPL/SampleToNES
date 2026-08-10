#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" == "Darwin" ]]; then
    exec bash "${SCRIPT_DIR}/scripts/macos/build/no_bundle.sh" "./install.sh"
fi

source "${SCRIPT_DIR}/scripts/linux/lib/root.sh"

source "${SCRIPT_DIR}/scripts/linux/build/python.sh"
source "${SCRIPT_DIR}/scripts/linux/build/venv.sh"
bash "${SCRIPT_DIR}/scripts/linux/build/sampletones.sh" "$@"
bash "${SCRIPT_DIR}/scripts/linux/build/build.sh" "$@"
