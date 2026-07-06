#!/usr/bin/env bash

set -e

echo "Installing system dependencies (requires sudo)"
sudo apt-get update
sudo apt-get install -y python3-tk tk-dev tcl-dev libportaudio2 libasound-dev libpulse-dev portaudio19-dev
echo "System dependencies installed."
