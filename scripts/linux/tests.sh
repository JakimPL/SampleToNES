#!/usr/bin/env bash

set +e

echo "Running unit test..."
python -m pytest src/ --doctest-modules --no-cov
DOCTEST_EXIT=$?

python -m pytest --cov=src/sampletones
PYTEST_EXIT=$?

if [[ $DOCTEST_EXIT -ne 0 ]] || [[ $PYTEST_EXIT -ne 0 ]]; then
    echo "Unit tests failed."
    exit 1
fi

echo "All tests passed."
exit 0