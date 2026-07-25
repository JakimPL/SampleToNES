#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/../lib/root.sh"

PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
VENV_DIR="$PROJECT_DIR/.venv-build"
VENV_PY="$VENV_DIR/bin/python"

RELEASE=0
BUNDLE_ARGS=(--onefile)
RELEASE_HOOK_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--release" ]]; then
        echo "Release build: onedir bundle, injecting release deployment configuration"
        RELEASE=1
        BUNDLE_ARGS=(--onedir)
        RELEASE_HOOK_ARGS=(--runtime-hook scripts/release_env_hook.py)
    fi
done

echo "Building executable..."
"$VENV_PY" -m pip install pyinstaller

"$VENV_PY" -m PyInstaller --name sampletones \
    "${BUNDLE_ARGS[@]}" \
    --noconfirm \
    --distpath ./bin \
    --icon "src/sampletones_assets/icons/sampletones.png" \
    --add-data "src/sampletones_assets/icons:assets/icons" \
    --add-data "src/sampletones_assets/fonts:assets/fonts" \
    --add-data "src/sampletones_config:config" \
    --copy-metadata sampletones \
    "${RELEASE_HOOK_ARGS[@]}" \
    "src/sampletones/__main__.py"

if [[ "${RELEASE}" == "1" ]]; then
    EXECUTABLE="bin/sampletones/sampletones"
else
    EXECUTABLE="bin/sampletones"
fi

if [[ ! -x "${EXECUTABLE}" ]]; then
    echo "Build failed."
    exit 1
fi

if [[ "${RELEASE}" == "1" ]]; then
    for notice in LICENSE THIRD-PARTY-NOTICES.md THIRD-PARTY-LICENSES.txt; do
        cp "${notice}" "bin/sampletones/${notice}"
    done
    echo "Bundled notices: LICENSE, THIRD-PARTY-NOTICES.md, THIRD-PARTY-LICENSES.txt"
fi

echo "Build complete: ./${EXECUTABLE}"
