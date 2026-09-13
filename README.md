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
* exporting reconstructed audio as FamiTracker `.fti` instruments, Bitphase `.json` instrument presets, `.nsf` programs the NES itself plays, or `.wav`

## Installation

You can install _SampleToNES_ in three ways:

- **Download a release** for Windows or Linux from the [releases page](https://github.com/JakimPL/SampleToNES/releases), extract it, and start `sampletones`.
- **Install from PyPI** on Windows, macOS or Linux. You need Python 3.12 or newer:

  ```sh
  uv tool install sampletones      # or: pipx install sampletones
  sampletones
  ```

- **Run from source** with Python 3.12 or newer and [uv](https://docs.astral.sh/uv/): `make system-deps`, `make setup`, then `make run`.

An NVIDIA graphics card can speed up conversion. The [installation guide](https://github.com/JakimPL/SampleToNES/blob/main/docs/guide/installation.md) covers the system libraries each way needs, GPU support, and building a standalone app yourself.

## Usage

### Where your files are stored

Your configuration, instruction libraries (`.ins`), and reconstructions (`.stn`) live under your documents folder, in `SampleToNES/`:

- Windows: `C:\Users\<user>\Documents\SampleToNES`
- Linux: `/home/<user>/Documents/SampleToNES`
- macOS: `/Users/<user>/Documents/SampleToNES`

### Command line

Every operation is a named command, and `sampletones` alone starts the interface:

```sh
sampletones run --config <config-path>                            # start with a custom config
sampletones open <project-path>                                   # start with a project, reconstruction or library loaded
sampletones convert <audio-path> --config <config-path> -o <out>  # reconstruct a recording without the GUI
sampletones library --config <config-path>                        # generate an instruction library
```

Run `sampletones --help` for the commands and `sampletones <command> --help` for a command's options. The [command-line guide](https://github.com/JakimPL/SampleToNES/blob/main/docs/guide/command-line.md) explains them.

## Documentation

The [user guide](https://github.com/JakimPL/SampleToNES/tree/main/docs/guide) explains how to use the app, step by step. The rest of [`docs/`](https://github.com/JakimPL/SampleToNES/tree/main/docs) covers the reconstruction algorithms, the file formats, the Python API and the developer notes.

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
