# Instruction library

This page defines what an instruction library is and what keys it. Read it before changing how a library
is generated or how its key is built. [Reconstruction algorithms](reconstruction.md) describes the search
over the catalog. [Instruction libraries](../formats/instruction-libraries.md) documents the file.

An instruction library is the catalog of NES sounds _SampleToNES_ searches when it reconstructs audio. It
has every instruction a channel can play: each combination of pitch, volume, timbre and on/off state. Each
entry has the waveform its instruction produces and a description of its frequency content.
Reconstruction searches this catalog. For each slice of the input, the engine looks for the entries whose
combined sound is closest to that slice.

## Why the library is precomputed

The number of distinct instructions is large but fixed, and the same candidates are compared against every
frame of every sample. The library renders each candidate's waveform and analyzes its spectrum once, up
front. That turns the per-frame work into a lookup instead of a re-synthesis. A library is built once for
a given configuration and reused across every reconstruction that shares it.

## Phase independence

Two recordings of the same note can look completely different sample by sample, depending on where in its
cycle each one starts. That position is the phase. Each candidate's stored spectrum is an average over
many phase offsets, so a candidate matches a frame on the shape of its spectrum and not on where its cycle
begins. [The candidate catalog](reconstruction.md#31-the-candidate-catalog-library) describes how the
average is made.

## What a library is keyed by

A library depends on the configuration values that change the rendered waveforms or the way their spectra
are measured:

* the **sample rate** and **NES frequency**, which together set the length of a frame and so the length
  of each rendered waveform;
* the **spectrum method** (`fft`, `logfft` or `cqt`) and **transformation gamma**, which set how each
  waveform's frequency content is measured and weighted.

These values form the library's key. Changing any of them describes a different sound space, so it
selects a different library and generates a fresh one if none exists. The target audio is measured the
same way, so the library and the target always share one representation and their spectra are directly
comparable. [Spectrum methods](reconstruction.md#32-spectrum-methods-fft-log-fft-and-cqt) explains what the
spectrum method and gamma do.

## Versions and rebuilding

A library belongs to the version of _SampleToNES_ that built it. A library built by another version is
rebuilt in its place the first time a reconstruction needs it. A configuration with no library is built
the same way. Regenerating a library that already exists replaces it.
[Data compatibility](../development/release/compatibility.md) describes the version rule.

Building a library by hand is covered in the guide, under
[building a library yourself](../guide/converting.md#building-a-library-yourself).

On disk a library is a single `.ins` file whose name encodes its configuration key. See
[Instruction libraries](../formats/instruction-libraries.md) for the file format.
