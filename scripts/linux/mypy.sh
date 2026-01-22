#!/usr/bin/env bash

set +e

echo "Running type checking with mypy..."
if [ $# -eq 0 ]; then
    python -m mypy src/sampletones
else
    python -m mypy "$@"
fi
exit $?
