# SampleToNES documentation

_SampleToNES_ rebuilds an audio sample from the sound channels of the NES's 2A03 chip: two pulse
waves, a triangle and noise. You can arrange the results into a song. You can export them to
[FamiTracker](glossary.md#famitracker), to [Bitphase](glossary.md#bitphase), or as an `.nsf` program
the NES plays.

The sections below are grouped by what you want to do. The guide needs no prior knowledge. The concepts
and formats sections assume you have used the application. The API and development sections are for
programmers.

## Using the application

The [**guide**](guide/) walks through the application from installation onward.

- [Installation](guide/installation.md) — the ways to install it, and GPU acceleration.
- [Getting started](guide/getting-started.md) — your first reconstruction and your first song.
- [The interface](guide/interface.md) — the four tabs, the menus and the keyboard shortcuts.
- [Converting audio](guide/converting.md) — the Main tab: adding recordings, choosing channels and running a conversion.
- [Working with a reconstruction](guide/reconstruction.md) — the Reconstruction tab: listening, editing instruments and exporting.
- [The sequencer](guide/sequencer.md) — the tracker: writing a song from samples and instruments, exporting it and rendering it to audio.
- [Command line](guide/command-line.md) — running without the graphical interface.
- [Where your files live](guide/files.md) — the folders and file types _SampleToNES_ uses.
- [Configuration](guide/configuration.md) — the settings you can change, and where.

## How it works

The [**concepts**](concepts/) section explains the ideas behind the reconstruction. You can read it
without the source code.

- [Reconstruction algorithms](concepts/reconstruction.md) — how a sample becomes a stream of NES instructions.
- [Stems reconstruction](concepts/stems.md) — how the channels are shared between several stems.
- [Instruction library](concepts/instruction-library.md) — the catalog of NES sounds the search draws from.
- [Song compression](concepts/compression.md) — how a song fits into the space an NES program has for it.
- [Project](concepts/project.md) — a song and the reconstructions it is built from.

## Tools

The [**tools**](tools/) section covers the commands that measure _SampleToNES_ or produce examples.
Each page says how to run the command with no options, what it writes and every custom use.

- [Calibration](tools/calibration.md) — how well the reconstruction reproduces reference sounds, with every reconstruction written out to listen to.

## File formats

The [**formats**](formats/) section documents the files _SampleToNES_ reads and writes.

- [Instruction libraries](formats/instruction-libraries.md) — the `.ins` candidate catalog.
- [Reconstructions](formats/reconstructions.md) — the `.stn` reconstruction data.
- [Projects](formats/projects.md) — the `.stp` project bundle.
- [FamiTracker export](formats/famitracker.md) — the `.fti` instrument and `.ftm` module formats.
- [Bitphase export](formats/bitphase.md) — the `.btp` document and `.json` instrument preset formats.
- [NSF export](formats/nsf.md) — the `.nsf` program the console plays, and the song block inside it.
- [Configuration file](formats/configuration.md) — the `config.json` structure.

## Programming with SampleToNES

The [Python API](api/index.md) page shows how to use `sampletones` as a library, with worked
examples.

## Development

The [**development**](development/) section is for contributors. The pages at its top cover the
whole repository. The pages about the graphical application and about releases each have a directory.

- [Architecture](development/architecture.md) — the application's layers and the contracts between them.
- [Package layers](development/packages.md) — the packages of the repository, and the order they import each other in.
- [Tooling](development/tooling.md) — the `sampletones` command, the tools package and the bootstrap scripts, with what each runs on and what it may import.
- [Coding guidelines](development/guidelines.md) — conventions for the codebase.
- [Writing the documentation](development/documentation.md) — who each document is written for, and how it reads.
- [Console player](development/player.md) — the 6502 driver an `.nsf` carries, the codec that fits a song beside it, and how both are verified.
- [Progress](development/progress.md) — how a long operation reports progress, within one process and across worker processes.
- [Bugs and to-dos](development/bugs-and-todos.md) — the working ledger of known gaps.

### The application

- [Undo engine](development/application/undo.md) — the design of undo and redo.
- [Sequencer blocks](development/application/sequencer-blocks.md) — the rules copy, cut, paste and delete follow on both grids.
- [Keyboard and actions](development/application/keyboard.md) — how a press reaches behavior, and how an action is declared and shown.
- [Identifier vocabularies](development/application/vocabularies.md) — the keys display text is looked up by, and the tags DearPyGui knows a widget by.
- [Colors and palettes](development/application/palette.md) — how a color is written, composed, and handed to DearPyGui.
- [The render thread](development/application/render-thread.md) — how work reaches DearPyGui from another thread, and what each crossing costs.
- [Dialogs](development/application/dialogs.md) — how a dialog gets its size, and where it opens.
- [Playback](development/application/playback.md) — the audio transport shared by every view, and rendering the song to a file.
- [Reconstruction browser](development/application/browser.md) — how a reconstructions directory becomes the tree both browser tabs show, and what narrows it.
- [Stems in the application](development/application/stems.md) — the Stems card, and what an edit or a removal does to the per-frame record.
- [Configuration](development/application/config-organization.md) — how the YAML configuration package is laid out.

### Releases

- [Data compatibility](development/release/compatibility.md) — how a file saved by an older version is upgraded to the current format when it loads.
- [Dependencies](development/release/dependencies.md) — the libraries _SampleToNES_ builds on.

## Glossary

The [glossary](glossary.md) defines the terms the other pages link to: NES hardware, the reconstruction
pipeline and tracker concepts.
