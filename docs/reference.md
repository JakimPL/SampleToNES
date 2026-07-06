# Reference

_Provisional reference material moved out of the README; to be reorganized with the rest of the docs later._

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

See the README's _GPU acceleration_ section for enabling GPU acceleration.

### Serialization

Instruction libraries and reconstructions are serialized with [_MessagePack_](https://msgpack.org/) (the `msgpack` package). No external compiler or system dependency is required — it is installed automatically with the package.

### Linux (standalone executable)

Building a standalone executable on Linux needs the Tk and PortAudio system packages. Install them with `make system-deps` (or run `scripts/linux/build/dependencies.sh`), which holds the full list.
