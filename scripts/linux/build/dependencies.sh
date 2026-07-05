#!/usr/bin/env bash

set -e

echo "Install additional system dependencies? (y/N)"
read -r INSTALL_SYS_DEPS
if [[ "$INSTALL_SYS_DEPS" == "y" || "$INSTALL_SYS_DEPS" == "Y" ]]; then
    sudo apt-get update
    sudo apt-get install -y python3-tk tk-dev tcl-dev libportaudio2 libasound-dev libpulse-dev portaudio19-dev
    echo "Additional system dependencies installed."
else
    echo "Warning: Skipping system dependencies installation may lead to build failures."
fi
