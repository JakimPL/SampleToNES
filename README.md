# SampleToNES v0.2.4

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
- [uv](https://docs.astral.sh/uv/), recommended for development and running from source

### Standalone executable

The quickest way to get a ready-to-run build. Python 3.12 is the only prerequisite.

#### Windows
1. Make sure Python 3.12 is installed and available as `python` in your PATH.
2. Double-click `install.bat` in this folder. It will build a standalone `sampletones.exe` in the same directory.
3. Run `sampletones.exe` to start the application.

#### Linux
1. Make sure Python 3.12 is installed and available as `python3` in your PATH.
2. Open a terminal in this folder and run:
	```sh
	./install.sh
	```
	This will build a standalone `sampletones` executable in the same directory.
3. Run `./sampletones` to start the application.

For now, the installation script is adjusted to Debian-based distributions only.

### Run from source

Requires [uv](https://docs.astral.sh/uv/). `make` is recommended (included with most Linux and macOS systems); without it, run the equivalent `uv` commands directly.

1. Set up everything — creates the virtual environment, installs all dependencies (including dev tools), and installs `sampletones` as a global command:
    ```sh
    make setup
    ```
2. Run the application:
    ```sh
    make run        # from the project directory
    sampletones     # from any folder, thanks to the global install
    ```
    On Windows without `make`, use `run.bat` in place of `make run`.

`make setup` is the recommended entry point. To do the same steps manually with `uv`:
```sh
uv sync --group dev     # create the environment with dev tools
uv tool install .       # install the global `sampletones` command
uv run sampletones      # run from the project without the global install
```

To update the global command after pulling new changes, re-run `make setup` (or `uv tool install --force .`).

### GPU support (CUDA)

_SampleToNES_ can use CUDA for acceleration via [_CuPy_](https://cupy.dev/). GPU mode is enabled by the `gpu` extra.

#### Linux

On Linux, the `gpu` extra installs CuPy alongside the CUDA 12 libraries it needs (`libcudart` and `libnvrtc` for the elementwise kernels, `libcublas` for the constant-Q transform's matmul) as Python wheels. A compatible NVIDIA driver on the host is sufficient — no system CUDA toolkit required, regardless of which CUDA version (if any) is installed system-wide.

```sh
make setup GPU=1      # environment and global command, both with GPU support
```

Or with uv directly:
```sh
uv sync --group dev --extra gpu     # environment with GPU support and dev tooling
uv tool install ".[gpu]"            # global `sampletones` command with GPU support
```

#### Windows

On Windows, the `gpu` extra installs CuPy. GPU mode additionally requires the [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) (version 12.x), which provides `cudart64_12.dll`, `nvrtc64_120_0.dll`, and `cublas64_12.dll` (the last backs the constant-Q transform's matmul).

## Data structures

### Instruction data

To optimize sample reconstruction, all single-oscillator instructions are prerendered as samples with spectral information.

The instruction data depends on the following configuration properties:
* `nes_frequency` (NES frequency, usually NTSC or PAL)
* `sample_rate` (in Hz)
* `transformation_gamma`, which determines the transformation of the spectral information:
    * `0` - raw absolute values of Fourier Transform
    * `100` - absolute values transformed via $\log\left(1 + x\right)$ operation
    Intermediate values interpolate between these two.
    **Warning.** For now, only the extremal values, `0` and `100`, are working. This is going to be fixed in some next release.

Each set of parameters corresponds to a different instructions data, encoded by a configuration key.

Libraries are generated using the generator included in the application. They can be generated from the _Instructions_ tab of the application and explored using the application.

#### Data content

For each key, the data consists of single instructions. Each instruction contains:
* metadata
* instruction data
* a single waveform frame
* spectrum

##### Instructions

Prerendered instructions contain the following data:
* generator class (`pulse`/`triangle`/`noise`)
* instruction data (`on`/`pitch`/`period`/`volume`/`duty_cycle`/`short`)

Instructions contain basic information for all 2A03 oscillators:
* **on** (0-1): whether a generator is on (1) or off (0)
* **pitch** (33-119) for pulse and triangle generators, and **period** (0-15) for the noise generator
* **volume** (0-15) for pulse and noise generators
* **duty_cycle** (0-3) for pulse generators, and the **short** (0-1) flag for the noise generator

##### Waveform

Each instruction is prerendered as a sample containing the entire period of a wave (excluding the longest noise samples, which are trimmed to 1 second).

##### Spectrum

Within each waveform, each instruction data contains spectral information on the frequency distribution in the waveform, precalculated using Fast Fourier Transform.

#### File format

Instructions libraries are stored as `.ins` files in the user's documents folder, e.g.:

```
sr_44100_nf_30_ws_1615_tg_0_ch_283a31a50176c14faf36949913117e49.ins
```

The configuration is embedded in the file name:
* `sr_44100` corresponds to the sample rate 44100 Hz
* `nf_30` describes NES frequency of 30 Hz
* `ws_1615` is the size of the FFT transformation (1615 samples)
* `tg_0` encodes `transformation_gamma = 0`
* `ch_283a31a50176c14faf36949913117e49` is the config hash.

### Reconstructions

#### Generators

Generators are responsible for producing waveforms and keeping the internal state of the generators (phase and clock).

As in 2A03, there are four generators of three types:
* `pulse1`
* `pulse2`
* `triangle`
* `noise`

For the most part, generators are not used during the reconstruction: each single instruction is precalculated with spectral information.

#### Reconstructor

Reconstructor is the main object responsible for sample conversion. It uses generators defined in the generation configuration. You can use any combination of generators to reconstruct your samples.

By default, `pulse1`, `triangle`, and `noise` are turned on.

#### Reconstruction

Reconstruction is an object containing all conversion information. The most important ones are:

* `approximation`: The sum of all generator waveforms approximating the input wave.
* `approximations`: Partial approximations from all generators
* `instructions`: A dictionary of all FamiTracker instructions per each generator.
* `config`: A snapshot of the configuration used to reconstruct the audio
* `audio_filepath`: The path to the original audio file.

#### Generation options

_SampleToNES_ offers additional generation settings:

* `mixer`: For amplifying the NES waveforms. Too low values may result in clamped dynamics; too high values may cause quiet samples to be lost.
* `find_best_phase`: Tries to find the best phase for a sample to fit the frame. `True` by default. Allows ignoring phase shifts while searching for the best approximation.
* `fast_difference`: Instead of calculating the FFT of the audio remainder after finding partial approximations in a frame, it calculates the difference between spectral features only. Disabled by default, as it may lead to inaccurate approximations.
* `reset_phase`: Resets phases within each instruction. Not recommended.

For now, only `mixer` is present in the main application. Other values are experimental and may be edited in the JSON configuration file.

## Application files

All local files, that is:
* configuration (`config.json`)
* instruction libraries (`.ins`)
* reconstructions (`.stn`)

are stored in the default documents directory. The path depends on the operating system.

### Windows

The default path of the instruction data is:
```
C:\Users\<user>\Documents\SampleToNES\instructions
```

### Linux

Local files can be found in the following directory:
```
/home/<user>/Documents/SampleToNES/instructions
```

### macOS

Similarly, the default directory for macOS is:
```
/Users/<user>/Documents/SampleToNES/instructions
```

## CLI arguments

### Custom config

You can run the application with a custom config via:

```bash
sampletones --config <config-path>
```

or, shortly:

```bash
sampletones -c <config-path>
```

### Instructions data generation

_SampleToNES_ supports CLI arguments also for instructions data generation. To generate a library for a given config, run:

```bash
sampletones --generate --config <config-path>
```

If the config path is not provided, the default one is loaded.

### Sample reconstruction

Similarly, you can reconstruct a single WAV file or a directory using:

```bash
sampletones <path> --config <config-path>
```

You can also specify the output file via `--output` (`-o`):

```bash
sampletones <path> --config <config-path> --output <output-path>
```

However, this approach is discouraged, since the reconstruction files won't appear in the program application.

### Help

For more information, run:
```bash
sampletones --help
```

## Source code

Single elements of the `sampletones` Python package can be used as well.

SampleToNES exposes a variety of classes:

```python
from sampletones import (
    Config,  # generation configuration
    Window,  # FFT window
    InstructionLibrary,  # library
    Reconstruction,  # reconstruction data
    Reconstructor,  # object reconstructing an audio
    # Generators
    PulseGenerator,
    TriangleGenerator,
    NoiseGenerator,
    # Instructions
    PulseInstruction,
    TriangleInstruction,
    NoiseInstruction,
)
```
Currently, the API is not well documented. I hope that this will change in time.

### Code examples

#### Instruction waveform

```python
from sampletones import Config, PulseGenerator, PulseInstruction
from sampletones_core.audio.io import write_wave

# Load configuration
config = Config.load("config.json")

# Prepare generator and instruction
generator = PulseGenerator(config)
instruction = PulseInstruction(on=True, pitch=55, volume=7, duty_cycle=2)

# Generate waveform
audio = generator(instruction)

# Save audio file
sample_rate = config.sample_rate
write_wave("pulse.wav", sample_rate, audio)
```

The output will be a single `G2` square wave with a length of one frame.

By default, the generator stores the internal state after generation to continue the process. To disable that behavior, pass `save=False` when calling the generator:
```python
audio = generator(instruction, save=False)  # doesn't change the generator state
```

### Sample reconstruction

```python
from sampletones import Config, Reconstructor
from sampletones_core.audio.io import write_wave

# Load configuration
config = Config.load("config.json")

# Load data and prepare the reconstructor
reconstructor = Reconstructor(config)

# Reconstruct an audio file and save the reconstruction to a file
reconstruction = reconstructor("sample.wav")
reconstruction.save("reconstruction.stn")

# Save the reconstruction waveform
sample_rate = config.sample_rate
write_wave("reconstruction.wav", sample_rate, reconstruction.approximation)
```

## Dependencies

### Graphical interface

The graphical user interface is implemented with _DearPyGui_, a Python wrapper for _ImGui_ (https://www.dearimgui.com/).

### Core

The core depends on common Python packages:
* `numpy`
* `scipy`
* `librosa`
* `cupy` (optional; required for GPU mode)

See the [_GPU support (CUDA)_](#gpu-support-cuda) section for enabling GPU acceleration.

### Serialization

Instruction libraries and reconstructions are serialized with [_MessagePack_](https://msgpack.org/) (the `msgpack` package). No external compiler or system dependency is required — it is installed automatically with the package.

### Linux (standalone executable)

To build a standalone executable on Linux, additional `tkinter` development packages are required:
* `python3-tk`
* `tk-dev`
* `tcl-dev`

The `install.sh` script will prompt to install these packages during installation.
