# Projects

A project gathers a set of voices and arranges them into a song, saved as a single
`.stp` file. It is what the sequencer works with, and what you hand over when you
share a whole piece. See [Project](../concepts/project.md) for what a project is;
this page documents the file. [Reconstructions](reconstructions.md) documents the
converted audio a sample stands on.

## Structure

A `.stp` file is a zip archive with two kinds of member:

* **`project.json`** — the project document (below).
* **`reconstructions/<id>.stn`** — one [reconstruction](reconstructions.md) per
  sample, stored as its own `.stn` member and referenced from the document by its
  id.

Keeping the reconstructions in separate members lets `project.json` stay small
while the larger audio data travels alongside it in the same archive. A
[shape](../glossary.md#shape) carries no audio, so the document holds it whole.

### `project.json`

| Field | Contents |
| --- | --- |
| `format_version` | the project format version, checked for compatibility on load (see [Versioning](#versioning)) |
| `metadata` | the application name and version (managed automatically) |
| `info` | `title`, `author`, and `comment`, plus `created` and `modified` timestamps |
| `settings` | the engine settings: `nes_frequency`, `sample_rate`, `tempo`, `speed`, and the metric highlights `first_highlight` and `second_highlight` |
| `voices` | the song's voices, each told apart by its `kind` (below) |
| `song` | the arrangement (below) |

### `voices`

Every voice carries an `id`, a `name`, and the `loop_point` its envelopes repeat
from while a note is held, or `null` where they play once. The `kind` says what
else it carries:

| `kind` | Contents |
| --- | --- |
| `sample` | the `reconstruction_id` of its audio member |
| `shape` | its `envelopes` — the `volume`, `arpeggio` and `duty_cycle` values it writes, each a list of one item per tick — and the `root_pitch` and `root_period` those values are measured against |

### `song`

The arrangement across the four channels:

* `rows_per_pattern` — the row count every pattern in the song shares;
* `order` — the arrangement itself: an ordered list of frames, each frame mapping
  every channel to the pattern index it plays, or empty for a silent slot;
* `channels` — per channel, a pool of patterns, each pattern a list of rows. A row
  states the `command` its note column holds — the `voice_id` to start, or a
  note-off — along with its `transpose` and `volume`. The channel a voice sounds on
  is the one whose pool holds the row.

## Detached reconstructions

The reconstructions inside a project are
[detached](reconstructions.md#detached-reconstructions) from their original
source-audio paths, so a project stays portable — it carries everything it needs
and no path that would only mean something on the author's machine.

## Versioning

`project.json` records the project format version it was written with. On load,
_SampleToNES_ requires that version to match the one it supports and declines an
incompatible file rather than misreading it. A file written at a version the
upgrade chain reaches is migrated in memory to the current shape before
deserialization (see
[Data compatibility](../development/compatibility.md)). Unknown or extra fields
within a matching version are ignored, which leaves room for the format to grow.

The current format version is 1.2. Version 1.2 gathers `samples` into `voices`,
each record stating its `kind`, and names a row's note command by `voice_id` alone.
Version 1.1 named each channel pool by `name` and a row command's channel by
`channel_name`.
