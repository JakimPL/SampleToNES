# SampleToNES documentation

_SampleToNES_ approximates an audio sample using only the sound channels of the
NES's 2A03 chip — two pulse waves, a triangle and noise — and lets you arrange
the results into a song and export them to [FamiTracker](glossary.md#famitracker),
to [Bitphase](glossary.md#bitphase), or as an `.nsf` program the console itself plays.
This is the documentation for using it, understanding how it works, and building
on it.

The sections below are grouped by what you want to do. They assume different
starting points: the guide needs no prior knowledge, the concepts and formats
sections assume you have used the application, and the API and development
sections are written for programmers.

## Using the application

The [**guide**](guide/) walks through the application from installation onward.

- [Installation](guide/installation.md) — the standalone build, running from source, and GPU acceleration.
- [Getting started](guide/getting-started.md) — your first reconstruction and your first song.
- [The interface](guide/interface.md) — the Main, Reconstructions, and Instructions tabs, and the menus.
- [The sequencer](guide/sequencer.md) — the tracker: arranging samples into a song, exporting a module, and rendering it to audio.
- [Command line](guide/command-line.md) — running without the graphical interface.
- [Where your files live](guide/files.md) — the folders and file types _SampleToNES_ uses.
- [Configuration](guide/configuration.md) — the settings you can change, and where.

## How it works

The [**concepts**](concepts/) section explains the ideas behind the
reconstruction. It is written to be read without the source code.

- [Reconstruction algorithms](concepts/reconstruction.md) — how a sample becomes a stream of NES instructions.
- [Stems reconstruction](concepts/stems.md) — how one reconstruction is assigned across several stems.
- [Instruction library](concepts/instruction-library.md) — the catalogue of NES sounds the search draws from.
- [Project](concepts/project.md) — a whole composition: a song and the reconstructions it is built from.
- [Calibration](concepts/calibration.md) — how the reconstruction's settings are tuned by experiment.

## File formats

The [**formats**](formats/) section documents the files _SampleToNES_ reads and writes.

- [Instruction libraries](formats/instruction-libraries.md) — the `.ins` candidate catalogue.
- [Reconstructions](formats/reconstructions.md) — the `.stn` reconstruction data.
- [Projects](formats/projects.md) — the `.stp` project bundle.
- [FamiTracker export](formats/famitracker.md) — the `.fti` instrument and `.ftm` module formats.
- [Bitphase export](formats/bitphase.md) — the `.btp` document and `.json` instrument preset formats.
- [Configuration file](formats/configuration.md) — the `config.json` structure.

## Programming with SampleToNES

The [Python API](api/index.md) covers using `sampletones` as a library, with
worked examples.

## Development

The [**development**](development/) section is for contributors.

- [Architecture](development/architecture.md) — the application's layers and the contracts between them.
- [Package layers](development/packages.md) — the packages the repository divides into, and the order they import each other in.
- [Undo engine](development/undo.md) — the design of the undo/redo subsystem.
- [Sequencer blocks](development/sequencer-blocks.md) — the rules copy, cut, paste and delete follow on both grids.
- [Playback](development/playback.md) — the audio transport shared by every view, and rendering the song to a file.
- [Reconstruction browser](development/browser.md) — how a reconstructions directory becomes the tree both browser tabs render, and what narrows it.
- [Configuration](development/config-organization.md) — how the YAML configuration package is laid out.
- [Coding guidelines](development/guidelines.md) — conventions for the codebase.
- [Dependencies](development/dependencies.md) — the libraries _SampleToNES_ builds on.
- [Bugs and to-dos](development/bugs-and-todos.md) — the working ledger of known gaps.

## Glossary

The [glossary](glossary.md) defines the recurring terms — NES hardware, the
reconstruction pipeline, and tracker concepts — that the other documents link to.
