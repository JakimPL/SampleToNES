# Command line

You can run _SampleToNES_ from a terminal: to reconstruct without opening the interface, to
generate a library, or to open a file directly in the app. Every operation is a named command,
and `sampletones` alone starts the interface.

The command is `sampletones` when installed from source; a standalone build is the executable you
made (`./bin/sampletones` on Linux, `bin\sampletones.exe` on Windows).

## Commands

| Command | Purpose |
| --- | --- |
| `sampletones`, `sampletones run` | start the interface |
| `sampletones open <file>` | start the interface with a `.stp` project, a `.stn` reconstruction or an `.ins` library loaded |
| `sampletones convert <recording>...` | reconstruct recordings into a `.stn` file, or every recording under one folder |
| `sampletones library` | build the instruction library for a configuration, then exit |
| `sampletones self-check` | verify that this build's imports, bundled resources and configuration files are all usable, then exit |
| `sampletones --version` | print the version |

Every command lists its options with `--help`.

## Common tasks

* **Reconstruct a file** — `sampletones convert input.wav -o output.stn`
* **Reconstruct a folder** — `sampletones convert path/to/folder` reconstructs every audio
  file inside it, into the reconstructions folder your configuration names.
* **Choose the channels** — add `--channels pulse1,pulse2` to reconstruct onto those two
  alone; without it a run uses pulse 1, triangle, and noise.
* **Mix several recordings into one reconstruction** — `sampletones convert bass.wav lead.wav
  --stems stems.json`. The stems file describes the same setup the interface's stems list
  builds: one entry per recording, in order, each naming the channels it may occupy and the
  ones it bends. The command prints which recording plays under which stem before it starts.
  [Reconstructions](../formats/reconstructions.md) shows the file.
* **Use a specific configuration** — add `--config my-config.json` to `run`, `open`, `convert`
  or `library`; otherwise your saved configuration is used (`config.json`, or built-in defaults
  if you have not saved one yet).
* **Generate a library and exit** — `sampletones library --config my-config.json`

GPU acceleration is selected at setup, not per run: `make setup` detects a supported
NVIDIA driver and installs the matching build (`make setup GPU=0` forces the CPU
backend) — see [Installation](installation.md).
