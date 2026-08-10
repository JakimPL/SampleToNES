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

## Audio playback

Playback goes through PortAudio, reached with the `pyaudio` package. PyPI carries `pyaudio` wheels for Windows, so Linux and macOS compile it on install and need the PortAudio headers and library on the machine. Linux takes them from the distribution packages listed in `scripts/linux/build/dependencies.sh`; macOS takes them from Homebrew through `scripts/macos/build/dependencies.sh`.

Compiling on macOS also depends on the interpreter's architecture. The python.org installer ships a universal2 build, which compiles extensions for both Apple Silicon and Intel, while Homebrew's `libportaudio` carries the machine's own architecture. Pinning `ARCHFLAGS` to `uname -m` settles it on the native one: `make setup` sets it directly, and the CI workflows take it from `scripts/macos/build/build_env.sh`, which reports it as a `KEY=VALUE` line alongside the PortAudio prefix for a Homebrew installed outside its usual place.

## File dialogs

Dialogs open through the XDG desktop portal (`org.freedesktop.portal.FileChooser`), reached over D-Bus with the pure-Python `jeepney` package on Linux. The portal lists every offered file type in its selector and reports back the one the user picked, which is what lets a save settle its format from the type chosen there. Where no portal answers, `kdialog` and `zenity` take over, and Tk last.

`jeepney` is declared for Linux alone, so the modules that speak to the portal are imported where it is installed: the application probes for it before reaching them, and the root `conftest.py` keeps them out of collection elsewhere, leaving the Linux runs of the suite to cover them.

## Linux (standalone executable)

Building a standalone executable on Linux needs the PortAudio, Tk and OpenGL/X11 system packages. Install them with `make system-deps` (or run `scripts/linux/build/dependencies.sh`), which holds the full list.

PortAudio is required. Tk backs the file dialogs where neither a portal nor a desktop tool answers, and `make release` requires it so the shipped executable stays self-contained.

The executable links against the glibc of the machine that builds it and runs on that version or newer, so a redistributable artifact belongs on the oldest Debian or Ubuntu release being supported.
