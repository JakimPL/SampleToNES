#!/usr/bin/env bash

set -e

RELEASE_HOOK_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--release" ]]; then
        echo "Release build: injecting release deployment configuration"
        RELEASE_HOOK_ARGS=(--runtime-hook scripts/release_env_hook.py)
    fi
done

pip install pyinstaller
echo "Building executable..."
pyinstaller --name sampletones \
    --onefile \
    --distpath . \
    --icon "src/sampletones_assets/icons/sampletones.png" \
    --add-data "src/sampletones_assets/icons:assets/icons" \
    --add-data "src/sampletones_assets/fonts:assets/fonts" \
    --add-data "src/sampletones_config:config" \
    --copy-metadata sampletones \
    "${RELEASE_HOOK_ARGS[@]}" \
    "src/sampletones/__main__.py"

if [[ -f sampletones ]]; then
    echo "Build complete: ./sampletones"
else
    echo "Build failed."
fi
