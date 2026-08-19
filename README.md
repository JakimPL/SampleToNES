# SampleToNES

[![PyPI](https://img.shields.io/pypi/v/sampletones.svg)](https://pypi.org/project/sampletones/)
[![Python](https://img.shields.io/pypi/pyversions/sampletones.svg)](https://pypi.org/project/sampletones/)
[![License](https://img.shields.io/pypi/l/sampletones.svg)](https://github.com/JakimPL/SampleToNES/blob/main/LICENSE)

<div align="center">
    <img src="https://raw.githubusercontent.com/JakimPL/SampleToNES/main/src/sampletones_assets/icons/sampletones.svg" alt="SampleToNES" width="64">
    <p><i>SampleToNES</i> v0.3.2</p>
</div>

## Overview

_SampleToNES_ (`sampletones`) is a desktop tool for people writing music for the NES 2A03 sound chip, mainly in [_FamiTracker_](http://famitracker.com/).

<div align="center">
    <img src="https://raw.githubusercontent.com/JakimPL/SampleToNES/main/docs/images/sampletones.png" alt="SampleToNES" width="640">
</div>

The core idea is to approximate an audio sample using only the chip's basic oscillators — two pulse channels, a triangle, and noise — **without any DPCM samples**.

A built-in sequencer lets you arrange the reconstructed samples into patterns and play them back inside the application, so you can experiment with the results before exporting the instruments into FamiTracker.

It supports:

* loading common audio formats: WAV, MP3, FLAC, OGG, AIFF, and AU
* a wide range of NES frequencies, from 15 Hz to 300 Hz, including the two most common standards:
    * NTSC (60 Hz)
    * PAL (50 Hz)
* various sample rates, from 8000 Hz to 192,000 Hz
* restricting the reconstruction to a chosen subset of oscillators:
    * `pulse1`
    * `pulse2`
    * `triangle`
    * `noise`
* exporting reconstructed audio as FamiTracker `.fti` instruments, Bitphase `.json` instrument presets, or `.wav`

## Installation

### Standalone bundle

The easiest way to use _SampleToNES_ is to download the release package for your platform from the
[releases page](https://github.com/JakimPL/SampleToNES/releases), extract it, and run
`sampletones` from inside the extracted folder. On Linux you may need `chmod +x sampletones`.

### Requirements

- Windows, macOS, or Linux
- Python 3.12 or newer (https://www.python.org/downloads/)

### From PyPI

The quickest way to get the `sampletones` command. Because _SampleToNES_ is an application
rather than a library, installing it into its own isolated environment is recommended:

```sh
uv tool install sampletones      # or: pipx install sampletones
sampletones                      # launch the GUI
```

A plain `pip install sampletones` into an active virtual environment works too.

To install with GPU support, request the `gpu` extra (see [GPU acceleration](#gpu-acceleration)):

```sh
uv tool install "sampletones[gpu]"
```

On Linux and macOS, audio playback and file dialogs rely on system libraries that come from
the platform's package manager. Install them first:

```sh
sudo apt-get install libportaudio2 libasound2 python3-tk    # Debian/Ubuntu
brew install portaudio                                      # macOS
```
### Building the executable yourself

You only need Python 3.12.

#### Windows

1. Install Python 3.12.
2. Double-click `install.bat`. It builds `bin\sampletones.exe`.
3. Double-click `bin\sampletones.exe` to start.

#### Linux

1. Install the audio and file-dialog system packages: `make system-deps` (or run `./scripts/linux/build/dependencies.sh`).
2. Install Python 3.12, then run `./install.sh` in a terminal. It builds a `bin/sampletones` executable.
3. Run `./bin/sampletones` to start.

### Run from source

For development. Requires [uv](https://docs.astral.sh/uv/) (and, on Linux, the system packages from the Linux steps above):

```sh
make setup      # create the environment and install the sampletones command
make run        # run the app
```

To update the global command after pulling new changes, re-run `make setup` (or `uv tool install --force .`).

### GPU acceleration

_SampleToNES_ can use an NVIDIA GPU (via [_CuPy_](https://cupy.dev/) and CUDA) to speed up instruction-library generation and reconstruction. `make setup` detects your NVIDIA driver and installs the matching CuPy build automatically:

```sh
make setup          # installs GPU support when a supported driver is present
make setup GPU=0    # forces the CPU (NumPy) backend
```

A current NVIDIA driver is all you need — the CUDA components ship with the CuPy build, on Linux and Windows alike. On macOS the app runs on the CPU.

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

Internals — the reconstruction algorithms, file formats, the Python API, and developer notes — live in [`docs/`](https://github.com/JakimPL/SampleToNES/tree/main/docs).

## License

_SampleToNES_ is released under the [MIT License](https://github.com/JakimPL/SampleToNES/blob/main/LICENSE).

The bundled fonts are third-party works under their own licenses (SIL Open Font License 1.1
and the Bitstream Vera license) and are not covered by the MIT License.

The standalone bundles on the [releases page](https://github.com/JakimPL/SampleToNES/releases)
additionally contain the Python runtime and every dependency, including several LGPL-licensed
libraries. [`THIRD-PARTY-NOTICES.md`](https://github.com/JakimPL/SampleToNES/blob/main/THIRD-PARTY-NOTICES.md)
lists everything they redistribute and what its license requires; the full license texts are in
[`THIRD-PARTY-LICENSES.txt`](https://github.com/JakimPL/SampleToNES/blob/main/THIRD-PARTY-LICENSES.txt)
and ship inside each bundle.
