# Command line

You can run _SampleToNES_ from a terminal. Use it to convert recordings in the terminal, to build
an instruction library, or to open a file in the app.

## Getting the command

How you run the command depends on how you installed _SampleToNES_:

- **Release download**: run `sampletones` in the extracted folder. On Windows the file is
  `sampletones.exe`.
- **PyPI**: `uv tool install sampletones` or `pipx install sampletones` puts `sampletones` on your
  path.
- **From source**: `make setup` puts `sampletones` on your path. A standalone build you make
  yourself is `./bin/sampletones` on Linux and `bin\sampletones.exe` on Windows.

[Installation](installation.md) explains each way.

## Commands

| Command | What it does |
| --- | --- |
| `sampletones` or `sampletones run` | Starts the app. |
| `sampletones open <file>` | Starts the app with a `.stp` project, a `.stn` reconstruction or an `.ins` library open. |
| `sampletones convert <recording>...` | Converts recordings into one `.stn` reconstruction, or converts every recording in a folder. |
| `sampletones library` | Builds the instruction library for a configuration, then exits. |
| `sampletones self-check` | Checks that the app can start: its code, its fonts and icons, and its configuration files. |
| `sampletones --version` or `sampletones -v` | Prints the version. |

Add `--help` to any command to see its options.

`sampletones --help` also lists commands for developing _SampleToNES_, such as `check` and `codec`.
They run from a copy of the source code. Add `--help` to one to see what it does.

`sampletones calibration` measures how well the app reconstructs a set of reference sounds.
[Calibration](../tools/calibration.md) explains how to run it and read the results.

## Options

- `--config <file>` or `-c <file>` uses a configuration file. It works with `run`, `open`,
  `convert` and `library`. Without it, the app uses your saved configuration, or the built-in
  defaults until you save one.
- `--output <file>` or `-o <file>` sets where `convert` saves the reconstruction. Without it, the
  reconstruction goes to the reconstructions folder of your configuration.
- `--channels <list>` sets the channels `convert` may use, for example `--channels pulse1,pulse2`.
  Without it, `convert` uses pulse 1, triangle and noise.
- `--stems <file>` gives `convert` a stems file, which it needs to mix several recordings. The file has
  one [stem](../glossary.md#stem) entry per recording.

A `convert` command takes either `--channels` or `--stems`.

## Common tasks

- **Convert one file**: `sampletones convert input.wav -o output.stn`
- **Convert a folder**: `sampletones convert path/to/folder`. Every recording in the folder
  becomes its own reconstruction, saved in your reconstructions folder.
- **Mix several recordings into one reconstruction**:
  `sampletones convert bass.wav lead.wav --stems stems.json`. The entries follow the order of the
  recordings. Each entry lists the channels the recording may use and the channels it
  [bends](../glossary.md#bend). [Reconstructions](../formats/reconstructions.md) shows the file.
- **Build a library**: `sampletones library --config my-config.json`

GPU support is chosen when you install _SampleToNES_. [Installation](installation.md) explains
how.
