# Reconstructions

## Generators

Generators are responsible for producing waveforms and keeping the internal state of the generators (phase and clock).

As in 2A03, there are four generators of three types:
* `pulse1`
* `pulse2`
* `triangle`
* `noise`

For the most part, generators are not used during the reconstruction: each single instruction is precalculated with spectral information.

## Reconstructor

Reconstructor is the main object responsible for sample conversion. It uses generators defined in the generation configuration. You can use any combination of generators to reconstruct your samples.

By default, `pulse1`, `triangle`, and `noise` are turned on.

## Reconstruction

Reconstruction is an object containing all conversion information. The most important ones are:

* `approximation`: The sum of all generator waveforms approximating the input wave.
* `approximations`: Partial approximations from all generators
* `instructions`: A dictionary of all FamiTracker instructions per each generator.
* `config`: A snapshot of the configuration used to reconstruct the audio
* `audio_filepath`: The path to the original audio file.

## Generation options

_SampleToNES_ offers additional generation settings:

* `mixer`: For amplifying the NES waveforms. Too low values may result in clamped dynamics; too high values may cause quiet samples to be lost.
* `find_best_phase`: Tries to find the best phase for a sample to fit the frame. `True` by default. Allows ignoring phase shifts while searching for the best approximation.
* `fast_difference`: Instead of calculating the FFT of the audio remainder after finding partial approximations in a frame, it calculates the difference between spectral features only. Disabled by default, as it may lead to inaccurate approximations.
* `reset_phase`: Resets phases within each instruction. Not recommended.

For now, only `mixer` is present in the main application. Other values are experimental and may be edited in the JSON configuration file.
