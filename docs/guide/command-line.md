# Command line

You can run _SampleToNES_ from a terminal — to reconstruct without opening the
interface, to generate a library, or to open a file directly in the app. Run it
with no arguments to launch the GUI as usual.

The command is `sampletones` when installed from source; a standalone build is the
executable you made (`./sampletones` on Linux, `sampletones.exe` on Windows).

## Common tasks

* **Launch the interface** — `sampletones`
* **Reconstruct a file** — `sampletones input.wav -o output.stn`
* **Reconstruct a folder** — `sampletones path/to/folder` reconstructs every audio
  file inside it.
* **Open a file in the app** — `sampletones song.stp` opens the interface preloaded
  with it; a `.stn` reconstruction or `.ins` library works the same way.
* **Use a specific configuration** — add `--config my-config.json`; otherwise your
  saved configuration is used (`config.json`, or built-in defaults if you have not
  saved one yet).
* **Generate a library and exit** — `sampletones --generate --config my-config.json`
* **Check the version** — `sampletones --version`

## Options

| Option | Purpose |
| --- | --- |
| `path` | (positional) an audio file or folder to reconstruct, or a `.stn` / `.ins` / `.stp` file to open in the app. Omit it to launch the interface. |
| `--output`, `-o` | output path for a reconstruction |
| `--config`, `-c` | path to a configuration `.json` (default: your saved `config.json`) |
| `--generate`, `-g` | build the instruction library for the configuration, then exit |
| `--version`, `-v` | print the version and exit |
| `--help`, `-h` | show the full option list |

GPU acceleration is selected at setup, not per run: `make setup` detects a supported
NVIDIA driver and installs the matching build (`make setup GPU=0` forces the CPU
backend) — see [Installation](installation.md).
