# Instruction library

An instruction library is the catalogue of NES sounds that _SampleToNES_
searches when it reconstructs audio. It holds every instruction a channel can
play — each combination of pitch, volume, timbre and on/off state — together
with the waveform that instruction produces and a description of its frequency
content. Reconstruction is then a matter of searching this catalogue: for each
slice of the input, the engine looks for the library entries whose combined
sound is closest to that slice. [Reconstruction algorithms](reconstruction.md)
describes that search; this page describes the catalogue it searches.

## Why the library is precomputed

The number of distinct instructions is large but fixed — a few thousand per
channel — and the same candidates are compared against every frame of every
sample. Rendering each candidate's waveform and analysing its spectrum once, up
front, turns the per-frame work into a lookup instead of a re-synthesis. A
library is therefore built once for a given configuration and reused across
every reconstruction that shares it.

The library is also a first-class artifact in its own right: you can generate,
browse and audition one from the _Instructions_ tab without reconstructing
anything, which is a good way to hear what a given channel and configuration can
actually produce.

## Phase independence

Two recordings of the same note can look completely different sample-by-sample
depending on where in its cycle each one starts — their phase. To keep matching
about *what a sound is* rather than *when it happened to begin*, each candidate's
stored spectrum is computed as an average over many phase offsets. The result is
essentially phase-independent, so a candidate matches a frame on the shape of its
spectrum, not on an accident of alignment.

## What a library is keyed by

A library depends on the configuration values that change the rendered waveforms
or the way their spectra are measured:

* the **sample rate** and **NES frequency**, which together set the length of a
  frame and so the length of each rendered waveform;
* the **spectrum method** (`fft`, `logfft` or `cqt`) and **transformation gamma**,
  which set how each waveform's frequency content is measured and weighted.

These values form the library's key. Changing any of them describes a different
sound space, so it selects a different library — and generates a fresh one if
none exists yet. What the spectrum method and gamma actually do is covered in
[Reconstruction algorithms](reconstruction.md) (§3.2–3.3), because the target
audio is measured the same way; the library and the target always share one
representation so their spectra are directly comparable.

## Generating and exploring

Generate a library from the _Instructions_ tab, or on the command line with
`sampletones --generate`. Generation renders every instruction and stores its
waveform and spectrum; a configuration that has no library yet is also built
automatically the first time a reconstruction needs it. Regenerating a library
that already exists replaces it.

The _Instructions_ tab lists the instructions in a library and shows the selected
one's waveform and spectrum alongside a player, so a library doubles as a way to
explore the raw material a reconstruction is assembled from.

On disk a library is a single `.ins` file whose name encodes its configuration
key; see [Instruction libraries](../formats/instruction-libraries.md) for the
file format.
