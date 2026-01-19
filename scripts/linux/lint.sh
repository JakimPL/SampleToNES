#!/usr/bin/env bash

set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/mypy.sh"
MYPY_EXIT=$?

bash "${SCRIPT_DIR}/pylint.sh"
PYLINT_EXIT=$?

if [[ $MYPY_EXIT -ne 0 ]] || [[ $PYLINT_EXIT -ne 0 ]]; then
    echo "Linting failed."
    exit 1
fi

echo "All linting checks passed."
exit 0
