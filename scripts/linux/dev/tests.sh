#!/usr/bin/env bash

set +e

echo "Running doctests..."
uv run python -m pytest src/ --doctest-modules --no-cov
DOCTEST_EXIT=$?

echo "Running pytest with coverage..."
uv run python -m pytest -n 6 --cov --ignore=tests/benchmarks
PYTEST_EXIT=$?

echo "Running benchmarks..."
uv run python -m pytest tests/benchmarks --no-cov
BENCHMARK_EXIT=$?

if [[ $DOCTEST_EXIT -ne 0 ]] || [[ $PYTEST_EXIT -ne 0 ]] || [[ $BENCHMARK_EXIT -ne 0 ]]; then
    echo "Tests failed."
    exit 1
fi

echo "All tests passed."
exit 0
