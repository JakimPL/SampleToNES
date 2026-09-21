# SampleToNES

[![PyPI](https://img.shields.io/pypi/v/sampletones.svg)](https://pypi.org/project/sampletones/)
[![Python](https://img.shields.io/pypi/pyversions/sampletones.svg)](https://pypi.org/project/sampletones/)
[![License](https://img.shields.io/pypi/l/sampletones.svg)](https://github.com/JakimPL/SampleToNES/blob/main/LICENSE)

<div align="center">
    <img src="https://raw.githubusercontent.com/JakimPL/SampleToNES/main/src/sampletones_assets/icons/sampletones.svg" alt="SampleToNES" width="64">
    <p><i>SampleToNES</i></p>
</div>

## Overview

_SampleToNES_ (`sampletones`) is a desktop tool for people writing music for the NES 2A03 sound chip, mainly in [_FamiTracker_](http://famitracker.com/).

<div align="center">
    <img src="https://raw.githubusercontent.com/JakimPL/SampleToNES/main/docs/images/sampletones.png" alt="SampleToNES" width="640">
</div>

The core idea is to approximate an audio sample using only the chip's basic oscillators — two pulse channels, a triangle, and noise — **without any DPCM samples**.

A built-in sequencer lets you arrange the reconstructed samples into patterns and play them back inside the application, so you can experiment with the results before exporting the instruments into FamiTracker.

With it you can:

* convert your own recordings — WAV, MP3, FLAC, OGG, AIFF or AU — into NES instruments
* choose which of the four channels each recording may use, and how loud it plays on them
* arrange the results into a song and play it back in the app
* export instruments and songs for:
  * [_FamiTracker_](http://famitracker.com/)
  * [_Bitphase_](https://bitphase.app/)
  * `.nsf` program
  * audio `.wav` file

## Installation

You can install _SampleToNES_ in three ways:

- **Download a release** for Windows or Linux from the [releases page](https://github.com/JakimPL/SampleToNES/releases), extract it, and start `sampletones`.
- **Install from PyPI** on Windows, macOS or Linux. You need Python 3.12 or newer. On Linux and
  macOS, install the audio and file dialog libraries first:

  ```sh
  sudo apt-get install libportaudio2 libasound2 python3-tk    # Debian and Ubuntu
  brew install portaudio                                      # macOS
  ```

  Then install the app and start it:

  ```sh
  uv tool install sampletones      # or: pipx install sampletones
  sampletones
  ```

- **Run from source** with Python 3.12 or newer and [uv](https://docs.astral.sh/uv/): `make system-deps`, `make setup`, then `make run`.

An NVIDIA graphics card can speed up conversion. The [installation guide](https://github.com/JakimPL/SampleToNES/blob/main/docs/guide/installation.md) covers the system libraries each way needs, GPU support, and building a standalone app yourself.

## Usage

`sampletones` starts the app. Your work is saved in a `SampleToNES` folder inside your documents
folder.

Every operation is also a named command — `sampletones convert <audio-path>` reconstructs a
recording without the interface, for example. Run `sampletones --help` for the list, and see the
[command-line guide](https://github.com/JakimPL/SampleToNES/blob/main/docs/guide/command-line.md).

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
