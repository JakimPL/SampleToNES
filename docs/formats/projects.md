# Projects

A project gathers a set of voices and arranges them into a song, saved as a single `.stp` file. The
sequencer works with it, and you hand it over to share a whole piece. See
[Project](../concepts/project.md) for what a project is. This page documents the file.
[Reconstructions](reconstructions.md) documents the converted audio a sample stands on.

## Structure

A `.stp` file is a zip archive with two kinds of member:

* **`project.json`** — the project document (below).
* **`reconstructions/<id>.stn`** — one [reconstruction](reconstructions.md) per
  sample, stored as its own `.stn` member and referenced from the document by its
  id. The archive deflates its members, so a member has the reconstruction's payload as it stands.

The reconstructions sit in separate members, so `project.json` stays small and the larger audio data
travels beside it in the same archive. An [instrument](../glossary.md#instrument) has no audio, so the
document holds it whole.

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

Every voice carries an `id` and a `name`. The `kind` says what else it carries:

| `kind` | Contents |
| --- | --- |
| `sample` | the `reconstruction_id` of its audio member |
| `instrument` | its `envelopes` — `volume`, `arpeggio` and `duty_cycle` — and the `initial_pitch` and `initial_period` those values are measured against |

Each envelope has its `items`, one per tick, and a `loop_point`: the item they repeat from while a note
is held. It is `null` where the items play once and the last item stands for as long as the note sounds.
See [loop point](../glossary.md#loop-point).

### `song`

The arrangement across the four channels:

| Field | Contents |
| --- | --- |
| `rows_per_pattern` | the row count every pattern in the song shares |
| `order` | an ordered list of frames, each mapping every channel to the pattern index it plays, or empty for a silent slot |
| `channels` | per channel, the `name` of the channel it drives and its pool of `patterns`, each pattern a list of rows |

A row has the `command` its note column holds (the `voice_id` to start, or a note-off), its `transpose`
and its `volume`. The channel a voice sounds on is the one whose pool has the row.

## Detached reconstructions

The reconstructions inside a project are [detached](reconstructions.md#detached-reconstructions) from
their original source-audio paths. A project therefore stays portable: it has everything it needs and no
path that means something only on the author's machine.

## Versioning

`project.json` records the project format version it was written with. A file at the supported version
loads as it stands. A file at an older version the upgrade chain reaches is migrated in memory to the
current shape first. Any other file is declined. [Data compatibility](../development/release/compatibility.md)
describes the chain. Unknown or extra fields within a matching version are ignored, which leaves room
for the format to grow.

The current format version is 1.1.
