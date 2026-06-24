#!/usr/bin/env bash

set -e

pip install pyinstaller
echo "Building executable..."
pyinstaller --name sampletones \
    --onefile \
    --distpath . \
    --icon "src/sampletones_assets/icons/sampletones.png" \
    --add-data "src/sampletones_assets/icons:assets/icons" \
    --add-data "src/sampletones_assets/fonts:assets/fonts" \
    --add-data "config:config" \
    "src/sampletones/__main__.py"

if [[ -f sampletones ]]; then
    echo "Build complete: ./sampletones"
else
    echo "Build failed."
fi
