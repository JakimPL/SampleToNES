# Project

A project is a whole composition in _SampleToNES_: a song written for the four NES
channels, together with the reconstructions it is built from. Where a
[reconstruction](reconstruction.md) is a single converted sound, a project holds
many of them and the arrangement that plays them, so an entire piece lives as one
file.

## What a project brings together

- the **samples** — the reconstructions you have imported, each a playable
  instrument in the song;
- the **song** — the arrangement itself: the patterns written for each channel and
  the order they play in;
- the **timing and details** — the tempo, speed, and NES frequency the song plays
  at, and the title, author, and comment that describe it.

You create and edit all of this on the [Sequencer](../guide/sequencer.md) tab, and
export the finished piece as a FamiTracker [module](../formats/famitracker.md).

## Self-contained and portable

A project embeds the reconstructions it uses rather than pointing at them elsewhere
on disk, so moving or sharing the file carries the whole composition — the
arrangement and every sound it needs. The embedded reconstructions are
[detached](../formats/reconstructions.md#detached-reconstructions) from their
source-audio paths, which mean nothing on another machine, so the project opens the
same wherever it goes.

## On disk

A project is saved as a `.stp` file — a small document describing the song and its
settings, alongside the embedded reconstructions.
[Projects](../formats/projects.md) documents that structure.
