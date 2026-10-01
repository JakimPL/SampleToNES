# Tracker playback check

The tracker playback check tells you whether a song exported to a tracker plays there the way
_SampleToNES_ plays it. It exports your projects, or a set of small projects that comes with
_SampleToNES_, and plays each exported file with the tracker's own playback code. It compares what the
sound chip plays on every channel and every engine tick with what _SampleToNES_ plays. Then it writes a
report of each difference.

Each tracker the check plays through is a *target*:

- `bitphase` exports a `.btp` document and plays it with the engine of a copy of the
  [Bitphase](../glossary.md#bitphase) source code.
- `famitracker` exports an `.ftm` module, has [FamiTracker](../glossary.md#famitracker) export it to an
  `.nsf` file, and plays that file the way a NES does.

Use it to:

- Check that your song plays in the tracker the way you wrote it.
- Check an export after changing it.
- Check an export against a newer version of the tracker.
- Find the tick, the row and the channel where the tracker plays a song differently.

## What it needs

For the `bitphase` target:

- [Node.js](https://nodejs.org), so that the `node` program runs in a terminal.
- A copy of the Bitphase source code with its packages installed. Clone
  `https://github.com/paator/bitphase` and run `pnpm install` in that folder.

The check reads that copy and leaves it as it is.

For the `famitracker` target:

- `FamiTracker.exe`, version 0.4.6, from [famitracker.com](http://famitracker.com).
- On Linux and macOS, [Wine](https://www.winehq.org), so that the `wine` program runs in a terminal. On
  Debian and Ubuntu, that is `sudo apt install wine`. On macOS, `brew install --cask wine-stable`.

FamiTracker exports the file without opening a window.

## Run it

In an installed copy, name the target and what it needs:

```
sampletones tracker-playback bitphase --checkout path/to/bitphase
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

- Small projects that each exercise one thing a song can do. They cover notes on every channel,
  volume rows, transpose rows, note-offs, hand-written instruments, samples with arpeggios and bends,
  noise at several periods in both modes, a tempo whose rows last unequal ticks, an order that revisits
  patterns, notes pushed below the lowest pitch, and a slice longer than a tracker instrument holds.
- The arrangement the example commands write, rebuilt from rendered sounds, at its own tempo and at a
  faster one.

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
`<project>.json`, every write Bitphase's engine made to the sound chip, tick by tick.

For the `famitracker` target, `documents/` has:

- `<project>.ftm`, ready to open in FamiTracker.
- `<project>.nsf`, the file FamiTracker exported, row markers included (see below).
- `<project>.json`, every write the NSF made to the sound chip, tick by tick.

Your projects are named after their files. When two files have the same name, the second one's files
get `-2` after the name.

## Reading the report

The report opens with a table of the projects. Each has the ticks each side plays and its verdict.
A section per project follows. It says which file the project came from, or what a corpus project
exercises. It also says what the export reported leaving out, such as an instrument it shortened. A
table then lists each difference. A line names:

- The channel.
- What differs. `audible` means the channel sounds on one side only. Otherwise the difference is in
  the `period`, the `volume`, or the `timbre`, which is the duty cycle on a pulse channel and the
  short mode on the noise channel.
- The first tick it shows on, with its frame and row.
- What each side sounds there.
- How many ticks show it.

Ticks that differ in the same way on the same channel are counted together. The lines under a
difference show later rows where both sides sound new values, so two causes that differ in the same
field show apart. The packaged settings set how many of those lines a difference shows.

A sound that ends in `counted down` is one the chip's own envelope or counters move on from the
level its registers set. The chip holds every other sound where its registers put it. The two differ
in `volume`.

A channel that is silent on both sides counts as alike. The report also says when the two sides
place a tick on different rows, or play a different number of ticks.

When your tempo makes rows last unequal ticks, FamiTracker spreads those ticks its own way, so its rows
start on other ticks than in _SampleToNES_. The report then shows the rows parting and differences that
follow from it.

## Options

- `bitphase --checkout <folder>`: the copy of the Bitphase source code. The `bitphase` target needs it.
- `famitracker --executable <file>`: `FamiTracker.exe`. The `famitracker` target needs it.
- `--project <file>`: a project file to check. Repeat it to check several. Without it, the run plays
  the corpus.
- `--output <folder>` or `-o <folder>`: where the run writes. Without it, the run writes into the
  timestamped folder described above.

## How it works

Each project is exported by the same code the app's export runs. The target then plays the file with
the tracker's own playback code and records every write the tracker makes to the sound chip's
registers on each tick.

- For `bitphase`, a script that comes with _SampleToNES_ plays the document through the Bitphase
  copy's own loader and renderer, and records each write its engine makes to the chip.
- For `famitracker`, FamiTracker exports the module to an NSF from its command line. The NSF holds
  FamiTracker's own sound driver, the program a NES runs to play the song. The check runs it on an
  emulated NES processor, the way an NSF player does, and records each write the driver makes to the
  chip.

An NSF doesn't say which row it plays. So the module FamiTracker exports has a marker on every row of
its DPCM channel, which _SampleToNES_ leaves empty. The marker sets the DPCM channel's output level to
one of a few low values, and the check reads it to know where each row starts. The other channels'
registers stay as the export wrote them. In an NSF player, the markers make the song sound a little
different: the level shifts the triangle and noise slightly, and each row clicks faintly. The `.ftm`
file the run keeps is the export as the app writes it, without the markers.

The same project is played through the song walk the sequencer and the NSF export share, and turned
into the register writes the NSF player makes. Both sides are then read the same way. The check keeps
the value each register holds on each tick, and reads from those values what the chip plays on each
channel: whether it sounds, its timer or noise period, its volume, and its duty cycle or noise mode.
The check reads what the tracker writes to the chip, so it sees the timer the chip receives, however
the tracker works it out from a note.

Tick 0 is the song's first tick on both sides, so the rows of a groove line up by themselves.

You run the check by hand. The test suite checks the corpus, the comparison and the report on their
own, and a tracker plays the files only when you run the command.
