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

if [[ "${RELEASE}" == "1" ]]; then
    EXECUTABLE="bin/sampletones/sampletones"
else
    EXECUTABLE="bin/sampletones"
fi

bash "$SCRIPT_DIR/preflight.sh" "$@"
bash "$SCRIPT_DIR/icons.sh"

if [[ -e "${PROJECT_DIR}/bin/sampletones" ]]; then
    echo "Removing the previous artifact: ./bin/sampletones"
    rm -rf "${PROJECT_DIR}/bin/sampletones"
fi

echo "Building executable..."
"$VENV_PY" -m PyInstaller --name sampletones \
    "${BUNDLE_ARGS[@]}" \
    --noconfirm \
    --distpath ./bin \
    --icon "src/sampletones_assets/icons/sampletones.png" \
    --add-data "src/sampletones_assets/icons:assets/icons" \
    --add-data "src/sampletones_assets/fonts:assets/fonts" \
    --add-data "src/sampletones_config:config" \
    --copy-metadata sampletones \
    --exclude-module PIL \
    "${RELEASE_HOOK_ARGS[@]}" \
    "src/sampletones/__main__.py"

if [[ ! -x "${EXECUTABLE}" ]]; then
    echo "Build failed: PyInstaller produced no executable at ./${EXECUTABLE}." >&2
    exit 1
fi

echo "Verifying the bundle..."
if ! "${PROJECT_DIR}/${EXECUTABLE}" --self-check; then
    echo "Build failed: ./${EXECUTABLE} did not pass its self-check." >&2
    exit 1
fi

if [[ "${RELEASE}" == "1" ]]; then
    for notice in LICENSE THIRD-PARTY-NOTICES.md THIRD-PARTY-LICENSES.txt; do
        cp "${notice}" "bin/sampletones/${notice}"
    done
    echo "Bundled notices: LICENSE, THIRD-PARTY-NOTICES.md, THIRD-PARTY-LICENSES.txt"
fi

echo "Build complete: ./${EXECUTABLE}"
