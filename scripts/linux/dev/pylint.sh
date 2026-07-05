#!/usr/bin/env bash

set +e

echo "Running linting with pylint..."
if [ $# -eq 0 ]; then
    uv run python -m pylint src/sampletones
else
    uv run python -m pylint "$@"
fi
exit $?
