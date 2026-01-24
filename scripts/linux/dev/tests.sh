#!/usr/bin/env bash

set +e

echo "Running doctests..."
python -m pytest src/ --doctest-modules --no-cov
DOCTEST_EXIT=$?

echo "Running pytest with coverage..."
python -m pytest --cov=src/sampletones
PYTEST_EXIT=$?

if [[ $DOCTEST_EXIT -ne 0 ]] || [[ $PYTEST_EXIT -ne 0 ]]; then
    echo "Tests failed."
    exit 1
fi

echo "All tests passed."
exit 0