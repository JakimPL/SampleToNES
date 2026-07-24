#!/usr/bin/env bash

_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

if [[ ! -d "${_PROJECT_ROOT}/src/sampletones" ]]; then
    echo "ERROR: SampleToNES project root not found (expected ${_PROJECT_ROOT}/src/sampletones)." >&2
    exit 1
fi

cd "${_PROJECT_ROOT}"
