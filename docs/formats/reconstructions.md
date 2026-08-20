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
* **source audio** — the path to the original recording, the stem paths when the
  reconstruction was built from several stems, or empty when the reconstruction
  is [detached](#detached-reconstructions);
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
  one waveform per channel that sounds;
* **per-channel instructions** — the instruction stream each channel plays, one
  [instruction](../glossary.md#instruction) per frame. This is the data a
  FamiTracker export is built from. A reconstruction holds a stream for every one
  of the four channels (`pulse1`, `pulse2`, `triangle`, `noise`), and a stream of
  no frames is a channel standing by: it is written by no export and costs
  nothing, while staying open to edit, so writing an envelope into it puts the
  channel in play and clearing every envelope takes it out again;
* **per-channel reference pitch** — the note each channel's arpeggio offsets are
  measured against, chosen once when the reconstruction is built and stored with
  the instructions it describes. An export reads the offsets against this pitch,
  so editing an arpeggio moves the frames around a base that stays put (see
  [FamiTracker export](famitracker.md));
* **per-channel held dimensions** — the envelopes each channel leaves to the
  player. An instruction states a value for every dimension of its frame, so this
  is what says which of them the instrument itself writes; the rest are the
  channel's, and the player keeps the value it already holds for them. A channel
  in play writes them all as it is built, and clearing an envelope in the
  instruments panel adds that dimension here;
* **stems assignment** — present when the reconstruction was built from several
  stems: the stems setup the assignment was made under and, per channel, the
  stem holding each frame (`stems_data`). A reconstruction from a single file
  carries none.

A channel standing by rests at a reference pitch of its own, so the first envelope
written into it sounds on a mid-range note, and it leaves every dimension it offers
to the player, which is the record a channel edited down to empty envelopes reaches
as well. A file naming a stream for the channels it plays alone reads as the whole
four, with the rest coming back standing by.

## Detached reconstructions

A reconstruction normally remembers the path to its source audio. Embedding one
in a [project](projects.md) makes it part of a shareable artifact, where an
absolute path on the author's machine means nothing to anyone else. Detaching
clears that path while keeping the approximation and instructions intact, so the
reconstruction stays self-contained and a saved project stays portable.

## Versioning

Each file records the reconstruction data-version it was written with. On load,
_SampleToNES_ requires that version to match the one it supports and declines a
file written by an incompatible version rather than misreading it. A file
written at a version the upgrade chain reaches is migrated in memory to the
current shape before deserialization (see
[Data compatibility](../development/compatibility.md)); the application version
is stored alongside the data version, for reference.

The current data version is 2.2. Version 2.2 renamed the per-channel stream and
approximation keys from `generator_name` to `channel_name` and the channel
selection under the embedded config from `generators` to `channels`; the enum
values stored inside (`pulse1`, `pulse2`, `triangle`, `noise`) never changed. A
reconstruction built from several stems also carries the optional `stems_data`
record; a file written before the record existed reads without one.

## Storage and export

`.stn` files live in the documents folder. They are binary
([MessagePack](https://msgpack.org/)) with the audio arrays embedded, so a file
is self-contained. The instruction streams can be exported to a tracker — one
instrument per channel, or a whole module — as described in
[FamiTracker export](famitracker.md) and [Bitphase export](bitphase.md).
