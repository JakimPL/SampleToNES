#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/../lib/root.sh"

PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
VENV_DIR="$PROJECT_DIR/.venv-build"
VENV_PY="$VENV_DIR/bin/python"

RELEASE=0
for arg in "$@"; do
    if [[ "$arg" == "--release" ]]; then
        RELEASE=1
    fi
done

can_import() {
    "$VENV_PY" -c "import $1" >/dev/null 2>&1
}

echo "Checking the build environment..."

if [[ ! -x "$VENV_PY" ]]; then
    echo "ERROR: build interpreter not found at ${VENV_PY}." >&2
    echo "Run './install.sh' from the project root to create the build environment." >&2
    exit 1
fi

if ! can_import pyaudio; then
    echo "ERROR: the build interpreter cannot import pyaudio, so the bundle would carry no audio playback." >&2
    echo "Run 'make system-deps' to install the PortAudio packages, then './install.sh' to reinstall dependencies." >&2
    exit 1
fi

echo "pyaudio: available"

if can_import tkinter; then
    echo "tkinter: available"
    exit 0
fi

if [[ "${RELEASE}" == "1" ]]; then
    echo "ERROR: the build interpreter cannot import tkinter, so a release bundle would depend on the" >&2
    echo "target machine providing zenity or kdialog for file dialogs." >&2
    echo "Run 'make system-deps' to install python3-tk, then build again." >&2
    exit 1
fi

echo "WARNING: the build interpreter cannot import tkinter."
echo "This bundle opens file dialogs through zenity or kdialog, which the machine running it has to provide."
echo "Run 'make system-deps' to install python3-tk and carry Tk as a self-contained fallback."
