#!/usr/bin/env bash

set +e

echo "Running type checking with mypy..."
if [ $# -eq 0 ]; then
    uv run python -m mypy
else
    uv run python -m mypy "$@"
fi
exit $?
