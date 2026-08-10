#!/usr/bin/env bash

set -e

PACKAGES=(
    portaudio
)

if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew is required to install the macOS system dependencies." >&2
    echo "Install it from https://brew.sh, then run this script again." >&2
    exit 1
fi

echo "Installing system dependencies through Homebrew"
brew install "${PACKAGES[@]}"
echo "System dependencies installed."
