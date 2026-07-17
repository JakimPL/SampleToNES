# Installation

There are two ways to run _SampleToNES_: a **standalone build** (the easiest, and
all most people need) and **running from source** (for development, and on macOS).
GPU acceleration is optional.

## Requirements

Everyone needs:

- A supported operating system: Windows, macOS, or Linux
- [Python 3.12 or newer](https://www.python.org/downloads/)

Some setups need a little more — each is covered in the relevant section below:

- **On Linux**, a few system packages are required to build or run: the Tk
  file-dialog and PortAudio audio libraries. Install them with `make system-deps`.
  On Windows and macOS they come with the official Python installer and the
  packaged dependencies, so nothing extra is needed.
- **Running from source** also needs [uv](https://docs.astral.sh/uv/).
- **GPU acceleration** needs an NVIDIA GPU with a current driver, and on Windows
  the NVIDIA CUDA Toolkit 12.x.

## Standalone build

A ready-to-run executable built on your machine. You only need Python 3.12.

### Windows

1. Install Python 3.12.
2. Double-click `install.bat`. It builds `sampletones.exe` in this folder.
3. Double-click `sampletones.exe` to start.

### Linux

1. Install the audio and file-dialog system packages: `make system-deps` (or run
   `./scripts/linux/build/dependencies.sh`).
2. Install Python 3.12, then run `./install.sh` in a terminal. It builds a
   `sampletones` executable.
3. Run `./sampletones` to start.

## Run from source

For development, and the way to run on macOS. Requires [uv](https://docs.astral.sh/uv/)
— and, on Linux, the system packages from the Linux steps above:

```sh
make setup      # create the environment and install the sampletones command
make run        # run the app
```

To update the global command after pulling new changes, re-run `make setup`.

## GPU acceleration

_SampleToNES_ can use an NVIDIA GPU (via [CuPy](https://cupy.dev/) and CUDA) to
speed up instruction-library generation and reconstruction. Enable it with the
`gpu` extra:

```sh
make setup GPU=1
```

You need an NVIDIA GPU with a current driver. On Windows, also install the
[NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) 12.x.

---

Once it runs, [Getting started](getting-started.md) walks through your first
reconstruction and your first song.
