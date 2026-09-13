# Python API

This page is for using _SampleToNES_ as a library in your own Python code. Use it to render instructions, generate a library, or run and export a reconstruction outside the application.

Names come from two packages:

- The names in the table below come from `sampletones`: `from sampletones import ...`.
- The examples also use a few helpers from `sampletones_core`: `write_wave`, `generate_library`, `DEFAULT_CHANNELS`, and the FamiTracker instrument writers. Import them with the full path each example shows.

## Public surface

```python
from sampletones import (
    Config,
    Window,
    InstructionLibrary,
    Reconstruction,
    Reconstructor,
    ChannelName,
    Generator,
    PulseGenerator,
    TriangleGenerator,
    NoiseGenerator,
    Instruction,
    PulseInstruction,
    TriangleInstruction,
    NoiseInstruction,
)
```

| Name | Purpose |
| --- | --- |
| `Config` | generation configuration; build it with `Config.load(path)` or `Config.default()` |
| `Window` | analysis window derived from a config (`Window.from_config(config)`) |
| `InstructionLibrary` | the library of candidate instructions a reconstruction searches |
| `Reconstructor` | runs a reconstruction: `Reconstructor(config, channels)("sample.wav")` |
| `Reconstruction` | the result of a reconstruction — its approximation audio, per-channel instructions, and the config used |
| `ChannelName` | enum naming the four channels: `pulse1`, `pulse2`, `triangle`, `noise` |
| `Generator` | shared base class of the oscillator generators |
| `PulseGenerator`, `TriangleGenerator`, `NoiseGenerator` | render one channel's waveform from an instruction |
| `Instruction` | shared base class of the per-frame channel instructions |
| `PulseInstruction`, `TriangleInstruction`, `NoiseInstruction` | one channel's settings for a single frame |

The package version is available as `sampletones.__version__`.

## Examples

### Render an instruction to a waveform

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

The output is a single `G2` square wave one frame long.

Each generator keeps an oscillator phase and clock. By default a call renders a standalone waveform and leaves that state where it was; pass `save=True` to advance it into the next call, so a sequence of instructions renders as one continuous signal:

```python
audio = generator(instruction, save=True)  # advances the generator state
```

### Generate an instruction library

A reconstruction searches an [instruction library](../formats/instruction-libraries.md) built for its configuration, so the library must exist first. Generate it once for a given config:

```python
from sampletones import Config
from sampletones_core.headless.library import generate_library

config = Config.load("config.json")
generate_library(config)  # renders every instruction and writes the .ins library
```

The same step is reached from the application's _Instructions_ tab, or on the command line with `sampletones library --config config.json`.

### Reconstruct a sample

With a library in place for the configuration:

```python
from sampletones import Config, Reconstructor
from sampletones_core.audio.io import write_wave
from sampletones_core.constants.enums import DEFAULT_CHANNELS

# Load configuration
config = Config.load("config.json")

# Prepare the reconstructor for the channels the run may use
reconstructor = Reconstructor(config, frozenset(DEFAULT_CHANNELS))

# Reconstruct an audio file and save the reconstruction
reconstruction = reconstructor("sample.wav")
reconstruction.save("reconstruction.stn")

# Save the reconstruction waveform
sample_rate = config.sample_rate
write_wave("reconstruction.wav", sample_rate, reconstruction.approximation)
```

### Load a reconstruction

`Reconstruction.load` reads a saved `.stn` back into a `Reconstruction`, carrying its approximation, per-channel instructions, and config:

```python
from sampletones import Reconstruction

reconstruction = Reconstruction.load("reconstruction.stn")
```

### Export instruments

`Reconstruction.export` returns the [envelopes](../formats/famitracker.md#b-the-2a03-instrument) of each channel. `build_instrument` turns one channel's envelopes into a FamiTracker instrument, and `write_fti` saves it as an `.fti` file:

```python
from sampletones import Reconstruction
from sampletones_core.formats.famitracker.builder import build_instrument
from sampletones_core.formats.famitracker.instrument import write_fti
from sampletones_core.formats.famitracker.specification.instruments import STANDALONE_INSTRUMENT_INDEX

reconstruction = Reconstruction.load("reconstruction.stn")

for channel, features in reconstruction.export().items():
    instrument = build_instrument(STANDALONE_INSTRUMENT_INDEX, channel.value, features)
    write_fti(f"{channel.value}.fti", instrument)
```

This writes one `.fti` per channel, named after the channel. A complete FamiTracker `.ftm` module is assembled from a project in the application, not from a single reconstruction — see [FamiTracker formats](../formats/famitracker.md).
