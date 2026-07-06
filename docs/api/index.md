# Python API

Single elements of the `sampletones` Python package can be used as well.

SampleToNES exposes a variety of classes:

```python
from sampletones import (
    Config,  # generation configuration
    Window,  # FFT window
    InstructionLibrary,  # library
    Reconstruction,  # reconstruction data
    Reconstructor,  # object reconstructing an audio
    GeneratorName,  # enum naming the four channels
    # Generators (Generator is their shared base class)
    Generator,
    PulseGenerator,
    TriangleGenerator,
    NoiseGenerator,
    # Instructions (Instruction is their shared base class)
    Instruction,
    PulseInstruction,
    TriangleInstruction,
    NoiseInstruction,
)
```
The package version is available as `sampletones.__version__`.

Currently, the API is not well documented. I hope that this will change in time.

## Code examples

### Instruction waveform

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

By default the generator produces the waveform without advancing its internal state. Pass `save=True` to carry the oscillator's phase and clock into the next call, so a sequence of instructions renders as one continuous signal:
```python
audio = generator(instruction, save=True)  # advances the generator state
```

## Sample reconstruction

Reconstruction searches an [instruction library](../formats/instruction-libraries.md) built for the configuration, so that library must exist first. Generate it once — from the application's _Instructions_ tab, or on the command line:

```sh
sampletones --generate --config config.json
```

With the library in place:

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
