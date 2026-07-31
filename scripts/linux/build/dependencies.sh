#!/usr/bin/env bash

set -e

PACKAGES=(
    # PortAudio: audio playback through pyaudio
    libportaudio2
    libasound-dev
    libpulse-dev
    portaudio19-dev
    # Tk: file dialogs where kdialog and zenity are absent
    python3-tk
    tk-dev
    tcl-dev
    # OpenGL and X11: the window DearPyGui opens through GLFW
    libgl1
    libegl1
    libx11-6
    libx11-xcb1
    libxcursor1
    libxi6
    libxinerama1
    libxrandr2
    libxrender1
    libxxf86vm1
)

echo "Installing system dependencies (requires sudo)"
sudo apt-get update
sudo apt-get install -y "${PACKAGES[@]}"
echo "System dependencies installed."
