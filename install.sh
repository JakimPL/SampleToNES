#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/scripts/linux/python.sh"
source "${SCRIPT_DIR}/scripts/linux/venv.sh"
source "${SCRIPT_DIR}/scripts/linux/dependencies.sh"
bash "${SCRIPT_DIR}/scripts/linux/install.sh" "$@"
bash "${SCRIPT_DIR}/scripts/linux/build.sh"
