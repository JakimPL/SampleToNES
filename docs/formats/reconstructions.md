# Reconstructions

A reconstruction is one converted audio sample: the per-channel instruction streams that
produce the NES [approximation](../glossary.md#approximation) of an original recording. It is
stored as a `.stn` file. [Reconstruction algorithms](../concepts/reconstruction.md) explains
how one is produced; this page documents the file.

The file states what is played rather than what it sounds like: the audio is rendered from the
instructions whenever it is needed, which keeps a file to a few megabytes and keeps what the
application shows in step with what an export plays.

## Contents

A `.stn` file holds:

* **metadata** — the application name and version, and the reconstruction
  data-version used to check compatibility on load (see [Versioning](#versioning));
* **id** — a unique identifier for the reconstruction;
* **configuration** — a frozen snapshot of the
  [generation configuration](../guide/configuration.md) used, so the file records
  exactly how it was made: sample rate, NES frequency, enabled channels, spectrum
  method, gamma, and the rest;
* **coefficient** — the [working level](../glossary.md#working-level-coefficient),
  the single scale factor applied to the input so its loudness fit the NES
  channels' range. Storing it lets the reconstruction and the original be shown
  and played on a common scale;
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
* **stems assignment** — the stems setup the reconstruction was built under, the
  recording behind each entry, and, per channel, the source holding each frame
  (`stems_data`). Every reconstruction carries one: a conversion from a single file
  records one stem covering every channel it plays. A frame whose channel is silent
  records the resting stem id, `-1`: a frame no source took, where a source's count
  of channels at once or a hierarchy left it free, and a frame the decoding settled
  on a silent instruction. A frame the reader wrote by hand records the authored
  stem id, `-2`, which answers to no recording and stands through every removal;
* **source audio** — per entry, the recording's name and the file it was read from,
  in the order the stems setup lists them. The name belongs to the document and the
  file to this machine, so a [detached](#detached-reconstructions) reconstruction
  keeps every name and states no location.

A channel standing by rests at a reference pitch of its own, so the first envelope
written into it sounds on a mid-range note, and it leaves every dimension it offers
to the player, which is the record a channel edited down to empty envelopes reaches
as well. A file naming a stream for the channels it plays alone reads as the whole
four, with the rest coming back standing by.

The stems setup is also what `sampletones convert --stems` reads, written as JSON with the
same fields: one entry per recording, in the order the recordings are given, each naming the
channels it may occupy, the ones it bends, the `drives` it pushes each of them at and the
`channel_cap` channels it may sound at once; and a hierarchy listing the stem ids by
precedence level. An entry stating no `drives` is read at unit drive on every channel it
holds, and one stating no `channel_cap` may sound all four. Two recordings, the first on the
pulses with its second pulse pushed harder and held to one channel a frame, the second on
the rest as it stands:

```json
{
  "entries": [
    {
      "id": 0,
      "settings": {
        "channels": ["pulse1", "pulse2"],
        "bends": ["pulse1", "pulse2"],
        "drives": {"pulse1": 1.0, "pulse2": 2.5},
        "channel_cap": 1
      }
    },
    {"id": 1, "settings": {"channels": ["triangle", "noise"], "bends": ["triangle"]}}
  ],
  "hierarchy": {"levels": [[0], [1]]}
}
```

## Detached reconstructions

A reconstruction normally remembers the file each of its recordings was read from.
Embedding one in a [project](projects.md) makes it part of a shareable artifact,
where an absolute path on the author's machine means nothing to anyone else.
Detaching lets those locations go while keeping the instructions, the stems
assignment and every recording's name, so the reconstruction stays self-contained,
a saved project stays portable, and the document still says which recordings it
was built from.

## Versioning

Each file records the reconstruction data-version it was written with. On load,
_SampleToNES_ requires that version to match the one it supports and declines a
file written by an incompatible version rather than misreading it. A file
written at a version the upgrade chain reaches is migrated in memory to the
current shape before deserialization (see
[Data compatibility](../development/release/compatibility.md)); the application version
is stored alongside the data version, for reference.

The current data version is 2.2. Version 2.2 renamed the per-channel stream and
approximation keys from `generator_name` to `channel_name`; the enum values
stored inside (`pulse1`, `pulse2`, `triangle`, `noise`) never changed. It also
records the source audio as one path per stem and carries the `stems_data` record
on every reconstruction; a file written before either existed is read with its
single path listed and a one-stem record synthesized from what it plays. The
channel selection lives on that record — each entry states the settings its stem
was converted with: the channels it held, the drive on each of them, and how many
of them it sounded at once — so the embedded configuration carries the scoring
settings alone. A file written before the entries carried drives is read with the
drive its configuration stated written onto every channel each entry holds, and
with the run's channel cap written onto every entry.

## Storage and export

`.stn` files live in the documents folder. They are binary
([MessagePack](https://msgpack.org/)) and self-contained: everything needed to
play a reconstruction is the instructions, the stems assignment and the frozen
configuration the file carries. The instruction streams can be exported to a
tracker — one instrument per channel, or a whole module — as described in
[FamiTracker export](famitracker.md) and [Bitphase export](bitphase.md).
