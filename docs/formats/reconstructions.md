# Reconstructions

A reconstruction is one converted audio sample: the per-channel instruction streams that
produce the NES [approximation](../glossary.md#approximation) of an original recording. It is
stored as a `.stn` file. [Reconstruction algorithms](../concepts/reconstruction.md) explains
how one is produced. This page documents the file.

The file has what is played, not what it sounds like. The audio is rendered from the instructions
whenever it is needed. That keeps the file small and keeps what the application shows in step with what
an export plays.

## Contents

A `.stn` file is one MessagePack map:

| Field | Contents |
| --- | --- |
| `metadata` | the application name and version, and the reconstruction data version checked on load (see [Versioning](#versioning)) |
| `id` | a unique identifier for the reconstruction |
| `config` | a frozen snapshot of the [generation configuration](../guide/configuration.md) it was made with: sample rate, NES frequency, spectrum method, gamma, and the rest |
| `coefficient` | the [working level](../glossary.md#working-level-coefficient), the single scale factor applied to the input to fit the NES channels' range. It lets the reconstruction and the original be shown and played on a common scale |
| `instructions_data` | one entry per channel (below) |
| `stems_data` | the stems setup, the recordings behind it, and which stem holds each frame (below) |

### `instructions_data`

One entry per channel:

| Field | Contents |
| --- | --- |
| `channel_name` | `pulse1`, `pulse2`, `triangle` or `noise` |
| `instructions` | the stream the channel plays, one [instruction](../glossary.md#instruction) per frame. A FamiTracker export is built from this |
| `initial_pitch` | the note the channel's arpeggio offsets are measured against, chosen when the reconstruction is built. An export reads the offsets against this pitch, so editing an arpeggio moves the frames around a fixed base (see [FamiTracker export](famitracker.md)) |
| `held_features` | the dimensions left to the channel. An export writes them as disabled slots, and every note sounds them at the value a song starts on |

A channel whose every frame rests is **standing by**, and its stream is stored as no frames at all. A
file that has streams only for the channels it plays reads as all four channels, and the rest come back
standing by.

### `stems_data`

| Field | Contents |
| --- | --- |
| `config` | the stems setup the conversion ran under: one entry per recording, and the hierarchy of levels |
| `sources` | one per entry: the `stem_id` it was converted as, the `name` it is known by, and the `path` it was read from, absent once [detached](#detached-reconstructions) |
| `assignments` | per channel, the `stem_ids` holding each frame, parallel to that channel's stream |
| `scale` | the [recording scale](../glossary.md#recording-scale): the factor the conversion divided every recording it read by, measured on the whole set before any recording left. Reading the recordings at it keeps each one at the level it held in the conversion. Absent in a file upgraded from data version 2.1, which holds one recording that reads at its own peak |

Every reconstruction has this record. A conversion from a single file records one stem covering every
channel it plays. Every entry holds a frame on some channel, unless no entry does: a recording left holding
none leaves the record, with its source and its place in the hierarchy. The recordings that stay keep their
ids. Two ids name no recording. `-1` is a resting frame. `-2` is a frame the reader wrote by
hand: it answers to no recording and survives every removal. A frame rests where its channel is silent:
where no source took it, where a source's channel count or the hierarchy left it free, or where decoding
settled on a silent instruction.

A recording's name belongs to the document and its path to this machine. A detached reconstruction
therefore keeps every name and has no location.

### The stems setup as JSON

`sampletones convert --stems` reads the same setup, written as JSON with the same fields. It has one
entry per recording, in the order the recordings are given. Each entry names the channels it may occupy,
the ones it bends, the `drives` it pushes each of them at and the `channel_cap` channels it may sound at
once. A hierarchy lists the stem ids by precedence level. A drive settles which instruction each frame
records while the conversion runs, so a reconstruction plays the instructions it names. An entry without
`drives` is read at unit drive on every channel it holds, and an entry without `channel_cap` may sound
all four. In this example, the first recording is on the pulses, with its second pulse pushed harder and
held to one channel a frame. The second recording is on the rest as it stands:

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

A reconstruction normally remembers the file each of its recordings was read from. Embedding one in a
[project](projects.md) makes it part of a shareable artifact, where an absolute path on the author's
machine means nothing to anyone else. Detaching lets those locations go and keeps the instructions, the
stems assignment and every recording's name. The reconstruction stays self-contained, a saved project
stays portable, and the document still says which recordings it was built from.

## Versioning

Each file records the reconstruction data version it was written with, and the application version
beside it for reference. A file at the supported version loads as it stands. A file at an older version
the upgrade chain reaches is migrated in memory to the current shape first. Any other file is declined.
[Data compatibility](../development/release/compatibility.md) describes the chain.

The current data version is 2.2. A file at data version 2.1 carries no stems record. Its upgrade records
one recording covering the channels the run handed out, and leaves the recording scale unmeasured.

## Storage and export

`.stn` files live in the documents folder. A file is a deflated [MessagePack](https://msgpack.org/)
payload and is self-contained: the instructions, the stems assignment and the frozen configuration are
everything needed to play it. The payload names every field of every frame, and a reconstruction has one
frame per channel per frame of audio. The names repeat for every frame, so they deflate to a small
fraction of the file. A payload stored plainly opens as it stands, so a file written by an earlier build
still opens.

The instruction streams can be exported to a tracker, as one instrument per channel or as a whole module.
See [FamiTracker export](famitracker.md) and [Bitphase export](bitphase.md).
