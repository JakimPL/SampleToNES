# Projects

A project gathers a set of reconstructions and arranges them into a song, saved
as a single `.stp` file. It is what the sequencer works with, and what you hand
over when you share a whole piece. See [Project](../concepts/project.md) for what a
project is; this page documents the file. [Reconstructions](reconstructions.md)
documents the individual samples it contains.

## Structure

A `.stp` file is a zip archive with two kinds of member:

* **`project.json`** — the project document (below).
* **`reconstructions/<id>.stn`** — one [reconstruction](reconstructions.md) per
  sample, stored as its own `.stn` member and referenced from the document by its
  id.

Keeping the reconstructions in separate members lets `project.json` stay small
while the larger audio data travels alongside it in the same archive.

### `project.json`

| Field | Contents |
| --- | --- |
| `format_version` | the project format version, checked for compatibility on load (see [Versioning](#versioning)) |
| `metadata` | the application name and version (managed automatically) |
| `info` | `title`, `author`, and `comment`, plus `created` and `modified` timestamps |
| `settings` | the engine settings: `nes_frequency`, `sample_rate`, `tempo`, and `speed` |
| `samples` | the song's samples — each an `id`, a `name`, and the `reconstruction_id` of its audio member |
| `song` | the arrangement (below) |

### `song`

The arrangement across the four channels:

* `rows_per_pattern` — the row count every pattern in the song shares;
* `order` — the arrangement itself: an ordered list of frames, each frame mapping
  every channel to the pattern index it plays, or empty for a silent slot;
* `channels` — per channel, a pool of patterns, each pattern a list of rows
  carrying the note, volume, and transpose data.

## Detached reconstructions

The reconstructions inside a project are
[detached](reconstructions.md#detached-reconstructions) from their original
source-audio paths, so a project stays portable — it carries everything it needs
and no path that would only mean something on the author's machine.

## Versioning

`project.json` records the project format version it was written with. On load,
_SampleToNES_ requires that version to match the one it supports and declines an
incompatible file rather than misreading it. Unknown or extra fields within a
matching version are ignored, which leaves room for the format to grow.
