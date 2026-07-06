# Projects

A project gathers a set of reconstructions and arranges them into a song, saved
as a single `.stp` file. It is what the sequencer works with, and what you hand
over when you share a whole piece. [Reconstructions](reconstructions.md)
documents the individual converted samples a project contains.

## Structure

A `.stp` file is a zip archive with two kinds of member:

* **`project.json`** — the project document, holding:
    * **format version** — the version of the project format, checked for
      compatibility on load (see [Versioning](#versioning));
    * **metadata** — the application name and version;
    * **info** — the project's title, author, and comment;
    * **settings** — playback and module settings, such as tempo, speed, rows per
      pattern, and NES frequency;
    * **samples** — a lightweight record of each reconstruction the project uses,
      referencing its data by id;
    * **song** — the arrangement: the pattern grid and the order the patterns play
      in, across the four channels.
* **`reconstructions/<id>.stn`** — one [reconstruction](reconstructions.md) per
  sample, stored as its own `.stn` member and referenced from `samples` by its id.

Keeping the reconstructions in separate members lets `project.json` stay small
while the larger audio data travels alongside it in the same archive.

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
