# Reconstructions

A reconstruction is one converted audio sample: the NES
[approximation](../glossary.md#approximation) of an original recording together
with the per-channel instruction streams that produce it. It is stored as a
`.stn` file. [Reconstruction algorithms](../concepts/reconstruction.md) explains
how one is produced; this page documents the file.

## Contents

A `.stn` file holds:

* **metadata** — the application name and version, and the reconstruction
  data-version used to check compatibility on load (see [Versioning](#versioning));
* **id** — a unique identifier for the reconstruction;
* **source audio** — the path to the original recording, or empty when the
  reconstruction is [detached](#detached-reconstructions);
* **configuration** — a frozen snapshot of the
  [generation configuration](../guide/configuration.md) used, so the file records
  exactly how it was made: sample rate, NES frequency, enabled channels, spectrum
  method, gamma, and the rest;
* **coefficient** — the [working level](../glossary.md#working-level-coefficient),
  the single scale factor applied to the input so its loudness fit the NES
  channels' range. Storing it lets the reconstruction and the original be shown
  and played on a common scale;
* **approximation** — the rendered NES audio: the sum of every channel's output,
  the closest match to the original;
* **per-channel approximations** — the audio each channel contributes on its own,
  one waveform per enabled channel (`pulse1`, `pulse2`, `triangle`, `noise`);
* **per-channel instructions** — the instruction stream each channel plays, one
  [instruction](../glossary.md#instruction) per frame. This is the data a
  FamiTracker export is built from;
* **per-channel reference pitch** — the note each channel's arpeggio offsets are
  measured against, chosen once when the reconstruction is built and stored with
  the instructions it describes. An export reads the offsets against this pitch,
  so editing an arpeggio moves the frames around a base that stays put (see
  [FamiTracker export](famitracker.md)).

## Detached reconstructions

A reconstruction normally remembers the path to its source audio. Embedding one
in a [project](projects.md) makes it part of a shareable artifact, where an
absolute path on the author's machine means nothing to anyone else. Detaching
clears that path while keeping the approximation and instructions intact, so the
reconstruction stays self-contained and a saved project stays portable.

## Versioning

Each file records the reconstruction data-version it was written with. On load,
_SampleToNES_ requires that version to match the one it supports and declines a
file written by an incompatible version rather than misreading it. The
application version is stored alongside it, for reference.

## Storage and export

`.stn` files live in the documents folder. They are binary
([MessagePack](https://msgpack.org/)) with the audio arrays embedded, so a file
is self-contained. The instruction streams can be exported to a tracker — one
instrument per channel, or a whole module — as described in
[FamiTracker export](famitracker.md) and [Bitphase export](bitphase.md).
