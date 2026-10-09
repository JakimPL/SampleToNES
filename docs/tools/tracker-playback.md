# Tracker playback check

The tracker playback check tells you whether a song exported to a tracker plays there the way
_SampleToNES_ plays it. It exports your projects, or a set of small projects that comes with
_SampleToNES_, and plays each exported file with the tracker's own playback code. It then compares,
[tick](../glossary.md#tick) by tick and channel by channel, what the sound chip plays with what
_SampleToNES_ plays. The report lists each difference.

Each tracker the check plays through is a *target*:

- `bitphase` exports a `.btp` document and plays it with the engine of a copy of the
  [Bitphase](../glossary.md#bitphase) source code.
- `famitracker` exports an `.ftm` module, has [FamiTracker](../glossary.md#famitracker) export it to an
  `.nsf` file, and plays that file the way a NES does.

Use it to:

- Check that your song plays in the tracker the way you wrote it.
- Check an export after you change the exporter or update the tracker.
- Find the tick, the row and the channel where the tracker plays a song differently.

The check needs the tracker installed, so it is not part of the automatic tests.

## What it needs

For the `bitphase` target:

- [Node.js](https://nodejs.org), so that the `node` program runs in a terminal.
- A copy of the Bitphase source code with its packages installed. Clone or download
  `https://github.com/paator/bitphase` and run `pnpm install` in that folder.

For the `famitracker` target:

- `FamiTracker.exe`, version 0.4.6, from [famitracker.com](http://famitracker.com).
- On Linux and macOS, [Wine](https://www.winehq.org), so that the `wine` program runs in a terminal. On
  Debian and Ubuntu, that is `sudo apt install wine`. On macOS, `brew install --cask wine-stable`.

## Run it

Each run needs one target. In an installed copy, name the target and what it needs, and run the
command twice to check both:

```
sampletones tracker-playback bitphase --directory path/to/bitphase
sampletones tracker-playback famitracker --executable path/to/FamiTracker.exe
```

To check your own song, add `--project` with its project file. Repeat it to check several songs in one
run:

```
sampletones tracker-playback famitracker --executable path/to/FamiTracker.exe --project my-song.stp
```

From a copy of the source code, `make tracker-playback` runs the targets you give it. `PROJECT` takes
one or more project files, separated by spaces:

```
make tracker-playback BITPHASE=path/to/bitphase FAMITRACKER=path/to/FamiTracker.exe PROJECT=my-song.stp
```

Without `--project`, the run plays the corpus that comes with _SampleToNES_:

- Small projects that each exercise one thing a song can do:
  - Notes on every channel.
  - Volume rows and transpose rows.
  - Note-offs.
  - Instruments with looping envelopes.
  - Samples with arpeggios and bends.
  - Noise at several periods, in both modes.
  - A tempo whose rows last unequal ticks.
  - An order that revisits patterns.
  - Notes below A-0, and bends past the lowest and highest note the chip plays.
- A longer arrangement, rebuilt from rendered sounds, at its own tempo and at a faster one.

The results go into a new folder inside the `tracker-playback` folder of your
[SampleToNES folder](../guide/files.md). The folder is named by the date and time the run started, for
example `run-20260930-124501`. When the run ends, the command prints each project's verdict and a link
to the report.

## What a run writes

| Path | Contents |
|---|---|
| `report.md` | the verdict for each project, and a table of every difference |
| `documents/` | each project as the export wrote it, and what the tracker's playback recorded of it |

For the `bitphase` target, `documents/` has `<project>.btp`, ready to open in Bitphase, and
`<project>.json`, what the sound chip held on every tick, for your own analysis.

For the `famitracker` target, `documents/` has:

- `<project>.ftm`, ready to open in FamiTracker.
- `<project>.nsf`, the file FamiTracker exported. It sounds slightly different from a normal export:
  the markers the check adds shift the triangle and noise a little and add a faint click on each row.
  The `.ftm` has no markers.
- `<project>.json`, what the sound chip held on every tick, for your own analysis.

Files are named after the project file. A second project with the same name gets `-2` appended.

## Reading the report

The first table has one row per project: how many ticks each side plays, and the verdict. The verdict
is `matches`, a number of differences, or `the rows or the length differ`. A section per project
follows. It says which file the project came from, or what a corpus project
exercises. It also says what the export reported leaving out, such as an instrument it shortened. A
table then lists each difference. A line names:

- The channel.
- What differs. `audible` means the channel sounds on one side only. Otherwise the difference is in
  the `period`, the `volume`, or the `timbre`, which is the duty cycle on a pulse channel and the
  short mode on the noise channel.
- The first tick it shows on, with its frame and row.
- What each side sounds there.
- How many ticks show it.

Ticks that differ in the same way on the same channel are counted together. Under each difference,
further lines show later rows where both sides play new values. This separates two causes that change
the same field. The `examples_per_difference` setting in `settings.yaml`, in the tool's
`tracker_playback/config` folder, sets how many lines a difference shows.

`counted down` after a sound means the chip's envelope or length counter keeps lowering the volume
after the registers are set. Other sounds hold the volume their registers set.

A channel that is silent on both sides shows no difference. The report also says when the two sides
place a tick on different rows, or play a different number of ticks.

With an uneven tempo, FamiTracker spreads the extra ticks differently, so its rows start on other
ticks than in _SampleToNES_. Expect row mismatches and the differences that follow from them. The
export is not at fault.

## Options

- `bitphase --directory <folder>`: the folder with the Bitphase source code. The `bitphase` target needs it.
- `famitracker --executable <file>`: `FamiTracker.exe`. The `famitracker` target needs it.
- `--project <file>`: a project file to check. Repeat it to check several. Without it, the run plays
  the corpus.
- `--output <folder>` or `-o <folder>`: the folder the run writes into, in place of the timestamped
  one.

## How it works

Each project is exported by the same code the app's export runs. The target then plays the file with
the tracker's own playback code and records the sound chip's registers on each tick.

- For `bitphase`, a script that comes with _SampleToNES_ plays the document through the Bitphase
  copy's own loader and renderer, and records each write its engine makes to the chip.
- For `famitracker`, FamiTracker exports the module to an NSF from its command line. The NSF holds
  FamiTracker's own sound driver, the program a NES runs to play the song. The check runs it on an
  emulated NES processor, the way an NSF player does, and records each write the driver makes to the
  chip.

To tell where each row starts, the module FamiTracker exports has a marker on every row of its DPCM
channel, which _SampleToNES_ leaves empty. The marker sets the DPCM channel's output level to one of a
few low values, and the check reads it. The other channels' registers stay as the export wrote them.

The reference side is _SampleToNES_'s own playback of the project, turned into chip register values.
Each side is reduced to what the chip plays on every channel on every tick: sounding or silent, timer
or noise period, volume, and duty cycle or noise mode. The two are then compared.
