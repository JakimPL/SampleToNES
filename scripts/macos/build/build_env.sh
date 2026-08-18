#!/usr/bin/env bash

set -e

if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew is required to locate the PortAudio headers and library." >&2
    echo "Run scripts/macos/build/dependencies.sh first." >&2
    exit 1
fi

PORTAUDIO_PREFIX=$(brew --prefix portaudio)

echo "CFLAGS=-I${PORTAUDIO_PREFIX}/include"
echo "LDFLAGS=-L${PORTAUDIO_PREFIX}/lib"
echo "ARCHFLAGS=-arch $(uname -m)"
