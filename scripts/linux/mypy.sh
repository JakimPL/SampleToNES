#!/usr/bin/env bash

set +e

echo "Running type checking with mypy..."
python -m mypy src/sampletones
exit $?