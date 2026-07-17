# SampleToNES v0.3.0

## Overview

_SampleToNES_ (`sampletones`) is a desktop tool for people writing music for the NES 2A03 sound chip, mainly in [_FamiTracker_](http://famitracker.com/).

The core idea is to approximate an audio sample using only the chip's basic oscillators — two pulse channels, a triangle, and noise — **without any DPCM samples**.

A built-in sequencer lets you arrange the reconstructed samples into patterns and play them back inside the application, so you can experiment with the results before exporting the instruments into FamiTracker.

It supports:

* loading common audio formats: WAV, MP3, FLAC, OGG, AIFF, and AU
* a wide range of NES frequencies, from 15 Hz to 600 Hz, including the two most common standards:
    * NTSC (60 Hz)
    * PAL (50 Hz)
* various sample rates, from 8000 Hz to 192,000 Hz
* restricting the reconstruction to a chosen subset of oscillators:
    * `pulse1`
    * `pulse2`
    * `triangle`
    * `noise`
* exporting reconstructed audio as FamiTracker `.fti` instruments or as `.wav`

## Installation

### Requirements

- Windows, macOS, or Linux
- Python 3.12 (https://www.python.org/downloads/)

### Standalone executable

The easiest way to use _SampleToNES_ — a ready-to-run build. You only need Python 3.12.

#### Windows

1. Install Python 3.12.
2. Double-click `install.bat`. It builds `sampletones.exe` in this folder.
3. Double-click `sampletones.exe` to start.

#### Linux

1. Install the audio and file-dialog system packages: `make system-deps` (or run `./scripts/linux/build/dependencies.sh`).
2. Install Python 3.12, then run `./install.sh` in a terminal. It builds a `sampletones` executable.
3. Run `./sampletones` to start.

### Run from source

For development. Requires [uv](https://docs.astral.sh/uv/) (and, on Linux, the system packages from the Linux steps above):

```sh
make setup      # create the environment and install the sampletones command
make run        # run the app
```

To update the global command after pulling new changes, re-run `make setup` (or `uv tool install --force .`).

### GPU acceleration

_SampleToNES_ can use an NVIDIA GPU (via [_CuPy_](https://cupy.dev/) and CUDA) to speed up instruction-library generation and reconstruction. Enable it with the `gpu` extra:

```sh
make setup GPU=1
```

You need an NVIDIA GPU with a current driver. On Windows, also install the [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) 12.x.

## Usage

### Where your files are stored

Your configuration, instruction libraries (`.ins`), and reconstructions (`.stn`) live under your documents folder, in `SampleToNES/`:

- Windows: `C:\Users\<user>\Documents\SampleToNES`
- Linux: `/home/<user>/Documents/SampleToNES`
- macOS: `/Users/<user>/Documents/SampleToNES`

### Command line

You can run without the GUI to use a custom config, generate an instruction library, or reconstruct a file:

```sh
sampletones --config <config-path>                                      # run with a custom config
sampletones --generate --config <config-path>                           # generate an instruction library
sampletones <audio-path> --config <config-path> --output <output-path>  # reconstruct an audio file
```

Run `sampletones --help` for all options.

## Documentation

Internals — the reconstruction algorithms, file formats, the Python API, and developer notes — live in [`docs/`](docs/).
