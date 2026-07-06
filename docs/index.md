# SampleToNES documentation

_SampleToNES_ approximates an audio sample using only the sound channels of the
NES's 2A03 chip — two pulse waves, a triangle and noise — and lets you arrange
the results into a song and export them to [FamiTracker](glossary.md#famitracker).
This is the documentation for using it, understanding how it works, and building
on it.

The sections below are grouped by what you want to do. They assume different
starting points: the guide needs no prior knowledge, the concepts and formats
sections assume you have used the application, and the API and development
sections are written for programmers.

## Using the application

The [**guide**](guide/) walks through the application from installation onward.

- [Installation](guide/installation.md) — the standalone build, running from source, and GPU acceleration.
- [The interface](guide/interface.md) — a tour of the four tabs and the settings windows.
- [Workflows](guide/workflows.md) — generating a library, reconstructing a sample, and exporting to FamiTracker.
- [Command line](guide/command-line.md) — running without the graphical interface.
- [Where your files live](guide/files.md) — the folders and file types _SampleToNES_ uses.
- [Configuration](guide/configuration.md) — the settings you can change, and where.

## How it works

The [**concepts**](concepts/) section explains the ideas behind the
reconstruction. It is written to be read without the source code.

- [Reconstruction algorithms](concepts/reconstruction.md) — how a sample becomes a stream of NES instructions.
- [Instruction library](concepts/instruction-library.md) — the catalogue of NES sounds the search draws from.
- [Calibration](concepts/calibration.md) — how the reconstruction's settings are tuned by experiment.

## File formats

The [**formats**](formats/) section documents the files _SampleToNES_ reads and writes.

- [Instruction libraries](formats/instruction-libraries.md) — the `.ins` candidate catalogue.
- [Reconstructions](formats/reconstructions.md) — the `.stn` reconstruction data.
- [Projects](formats/projects.md) — the `.stp` project bundle.
- [FamiTracker export](formats/famitracker.md) — the `.fti` instrument and `.ftm` module formats.

## Programming with SampleToNES

The [Python API](api/index.md) covers using `sampletones` as a library, with
worked examples.

## Development

The [**development**](development/) section is for contributors.

- [Architecture](development/architecture.md) — the application's layers and the contracts between them.
- [Undo engine](development/undo.md) — the design of the undo/redo subsystem.
- [Coding guidelines](development/guidelines.md) — conventions for the codebase.
- [Dependencies](development/dependencies.md) — the libraries _SampleToNES_ builds on.
- [Bugs and to-dos](development/bugs-and-todos.md) — the working ledger of known gaps.

## Glossary

The [glossary](glossary.md) defines the recurring terms — NES hardware, the
reconstruction pipeline, and tracker concepts — that the other documents link to.
