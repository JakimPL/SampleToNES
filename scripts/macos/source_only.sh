#!/usr/bin/env bash

set -e

OPERATION="${1:-this command}"

echo "ERROR: ${OPERATION} supports Linux and Windows." >&2
echo "On macOS, SampleToNES runs from source:" >&2
echo >&2
echo "    make setup" >&2
echo "    make run" >&2
echo >&2
echo "See docs/guide/installation.md for the full steps." >&2
exit 1
