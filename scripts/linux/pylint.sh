#!/usr/bin/env bash

set +e

echo "Running linting with pylint..."
python -m pylint src/sampletones
exit $?