# Dependencies

## Graphical interface

The graphical user interface is implemented with DearPyGui, a Python wrapper for ImGui (https://www.dearimgui.com/).

## Core

The core depends on common Python packages:
* `numpy`
* `scipy`
* `librosa`
* `cupy` (optional; required for GPU mode)

See the README's _GPU acceleration_ section for enabling GPU acceleration.

## Serialization

Instruction libraries and reconstructions are serialized with [MessagePack](https://msgpack.org/) (the `msgpack` package). No external compiler or system dependency is required — it is installed automatically with the package.

## Linux (standalone executable)

Building a standalone executable on Linux needs the Tk and PortAudio system packages. Install them with `make system-deps` (or run `scripts/linux/build/dependencies.sh`), which holds the full list.
