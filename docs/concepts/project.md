# Project

This page says what a project is and what it holds. Read it before changing what a saved project
contains. [Projects](../formats/projects.md) documents the file.

A project is a whole composition in _SampleToNES_: a song written for the four NES channels, with the
voices it is built from. A [reconstruction](reconstruction.md) is a single converted sound. A project has
many of them, the instruments written by hand beside them, and the arrangement that plays them all. An
entire piece lives in one file.

## What a project brings together

- The [**voices**](../glossary.md#voice): the reconstructions you have imported and the instruments you
  have written by hand. A [row](../glossary.md#row) can play any of them.
- The **song**: the [patterns](../glossary.md#pattern) written for each channel and the order they play
  in.
- The **settings and info**: the tempo, speed and NES frequency the song plays at, and the title, author
  and comment that describe it.

The [sequencer guide](../guide/sequencer.md) covers writing a project and exporting it.

## Self-contained and portable

A project stores the reconstructions it uses inside its own file. It also stores each hand-written
instrument there. Moving or sharing the file therefore moves the whole composition: the arrangement and
every sound it needs. The stored reconstructions are
[detached](../formats/reconstructions.md#detached-reconstructions) from their source-audio paths, because
those paths mean nothing on another machine. The project opens the same wherever it goes.

## On disk

A project is saved as a `.stp` file: a document describing the song and its settings, with the embedded
reconstructions beside it. [Projects](../formats/projects.md) documents that structure.
