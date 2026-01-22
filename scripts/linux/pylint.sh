#!/usr/bin/env bash

set +e

echo "Running linting with pylint..."
if [ $# -eq 0 ]; then
    python -m pylint src/sampletones
else
    python -m pylint "$@"
fi
exit $?
