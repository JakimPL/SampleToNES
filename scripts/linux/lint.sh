#!/usr/bin/env bash

set +e

echo "Running type checking with mypy..."
python -m mypy src/sampletones
MYPY_EXIT=$?

echo "Running linting with pylint..."
python -m pylint src/sampletones
PYLINT_EXIT=$?

if [[ $MYPY_EXIT -ne 0 ]] || [[ $PYLINT_EXIT -ne 0 ]]; then
    echo "Linting failed."
    exit 1
fi

echo "All linting checks passed."
exit 0
