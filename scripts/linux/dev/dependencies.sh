#!/usr/bin/env bash

set -e

echo "Install additional dev dependencies? (y/N)"
read -r INSTALL_DEV_DEPS
if [[ "$INSTALL_DEV_DEPS" == "y" || "$INSTALL_DEV_DEPS" == "Y" ]]; then
    sudo apt update
    sudo apt install -y flatbuffers-compiler
    echo "Additional dev dependencies installed."
fi
