# Python API

This page is for using _SampleToNES_ as a library from your own Python code. Everything you need is re-exported from the top-level `sampletones` package — its facade — so `from sampletones import ...` is the whole public surface. Consult this page when you want to render instructions, generate a library, or run and export a reconstruction outside the application.

A few lower-level helpers used in the examples (`write_wave`, `generate_library`) are not part of the facade; they are imported from `sampletones_core` with their full path, as shown.

## Public surface

```python
from sampletones import (
    Config,
    Window,
    InstructionLibrary,
    Reconstruction,
    Reconstructor,
    GeneratorName,
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
| `Reconstructor` | runs a reconstruction: `Reconstructor(config)("sample.wav")` |
| `Reconstruction` | the result of a reconstruction — its approximation audio, per-generator instructions, and the config used |
| `GeneratorName` | enum naming the four channels: `pulse1`, `pulse2`, `triangle`, `noise` |
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
from sampletones_core.scripts.library import generate_library

config = Config.load("config.json")
generate_library(config)  # renders every instruction and writes the .ins library
```

The same step is reached from the application's _Instructions_ tab, or on the command line with `sampletones --generate --config config.json`.

### Reconstruct a sample

With a library in place for the configuration:

```python
from sampletones import Config, Reconstructor
from sampletones_core.audio.io import write_wave

# Load configuration
config = Config.load("config.json")

# Prepare the reconstructor
reconstructor = Reconstructor(config)

# Reconstruct an audio file and save the reconstruction
reconstruction = reconstructor("sample.wav")
reconstruction.save("reconstruction.stn")

# Save the reconstruction waveform
sample_rate = config.sample_rate
write_wave("reconstruction.wav", sample_rate, reconstruction.approximation)
```

### Load a reconstruction

`Reconstruction.load` reads a saved `.stn` back into a `Reconstruction`, carrying its approximation, per-generator instructions, and config:

```python
from sampletones import Reconstruction

reconstruction = Reconstruction.load("reconstruction.stn")
```

### Export instruments

`Reconstruction.export` returns the per-channel [features](../formats/instruction-libraries.md), one entry per generator, and each set saves as a FamiTracker `.fti` instrument:

```python
from sampletones import Reconstruction

reconstruction = Reconstruction.load("reconstruction.stn")

for name, features in reconstruction.export().items():
    features.save(f"{name}.fti", instrument_name=str(name))
```

This writes one `.fti` per channel. A complete FamiTracker `.ftm` module is assembled from a project in the application, not from a single reconstruction — see [FamiTracker formats](../formats/famitracker.md).
