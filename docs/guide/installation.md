# Installation

You can install _SampleToNES_ in three ways:

- **Download a release.** This is the easiest way on Windows and Linux.
- **Install from PyPI.** This works on Windows, macOS and Linux.
- **Run from source.** Use this to change the code or to build the app yourself.

GPU acceleration is optional. The last section of this page explains it.

## Download a release

1. Open the [releases page](https://github.com/JakimPL/SampleToNES/releases).
2. Download the file for your system: Windows or Linux.
3. Extract the file.
4. Start `sampletones` in the extracted folder. On Windows, double-click `sampletones.exe`.

On Linux, you may need to make the file executable first: `chmod +x sampletones`.

## Install from PyPI

You need [Python 3.12 or newer](https://www.python.org/downloads/).

On Linux and macOS, install the audio and file dialog libraries first:

```sh
sudo apt-get install libportaudio2 libasound2 python3-tk    # Debian and Ubuntu
brew install portaudio                                      # macOS
```

Then install _SampleToNES_ in an environment of its own, and start it:

```sh
uv tool install sampletones      # or: pipx install sampletones
sampletones
```

You can also run `pip install sampletones` inside an active virtual environment.

## Run from source

You need:

- [Python 3.12 or newer](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/)
- `make`

Get the code and set it up:

```sh
git clone https://github.com/JakimPL/SampleToNES.git
cd SampleToNES
make system-deps    # Linux and macOS: installs the system libraries
make setup          # creates the environment and installs the sampletones command
make run            # starts the app
```

After you pull new changes, run `make setup` again.

### Build a standalone app

On Windows and Linux, you can build a standalone app from the source code:

- **Windows**: double-click `install.bat`. It builds `bin\sampletones.exe`.
- **Linux**: run `make system-deps`, then `./install.sh`. It builds `bin/sampletones`.

## GPU acceleration

_SampleToNES_ can use an NVIDIA graphics card to build libraries and convert recordings faster. It
needs an NVIDIA card with a current driver, on Windows or Linux. On macOS, the app uses the CPU.

- **From source**: `make setup` checks your NVIDIA driver and installs the matching GPU support.
  `make setup GPU=0` installs the app without GPU support.
- **From PyPI**: add the `gpu` extra, `uv tool install "sampletones[gpu]"`. If your driver supports
  CUDA 11 only, use the `gpu-cuda11` extra instead.

---

Once the app runs, [Getting started](getting-started.md) walks you through your first
reconstruction and your first song.
