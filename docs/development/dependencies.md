# Dependencies

## Graphical interface

The graphical user interface is implemented with DearPyGui, a Python wrapper for ImGui (https://www.dearimgui.com/).

## Core

The core depends on common Python packages:
* `numpy`
* `scipy`
* `librosa`
* `cupy` (optional; enables the GPU backend, with the build selected for your NVIDIA driver)

See [GPU acceleration](../guide/installation.md#gpu-acceleration) for enabling it.

## Serialization

Instruction libraries and reconstructions are serialized with [MessagePack](https://msgpack.org/) (the `msgpack` package). No external compiler or system dependency is required — it is installed automatically with the package.

## File dialogs

Dialogs open through the XDG desktop portal (`org.freedesktop.portal.FileChooser`), reached over D-Bus with the pure-Python `jeepney` package on Linux. The portal lists every offered file type in its selector and reports back the one the user picked, which is what lets a save settle its format from the type chosen there. Where no portal answers, `kdialog` and `zenity` take over, and Tk last.

## Linux (standalone executable)

Building a standalone executable on Linux needs the PortAudio, Tk and OpenGL/X11 system packages. Install them with `make system-deps` (or run `scripts/linux/build/dependencies.sh`), which holds the full list.

PortAudio is required. Tk backs the file dialogs where neither a portal nor a desktop tool answers, and `make release` requires it so the shipped executable stays self-contained.

The executable links against the glibc of the machine that builds it and runs on that version or newer, so a redistributable artifact belongs on the oldest Debian or Ubuntu release being supported.
