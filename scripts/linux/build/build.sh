#!/usr/bin/env bash

set -e

pip install pyinstaller
echo "Building executable..."
pyinstaller --name sampletones \
    --onefile \
    --distpath . \
    --icon "src/sampletones/assets/icons/sampletones.png" \
    --add-data "src/sampletones/assets/icons:assets/icons" \
    --add-data "src/sampletones/assets/fonts:assets/fonts" \
    "src/sampletones/__main__.py"

if [[ -f sampletones ]]; then
    echo "Build complete: ./sampletones"
else
    echo "Build failed."
fi
