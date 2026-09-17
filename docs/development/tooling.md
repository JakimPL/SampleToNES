# Tooling

This document governs how the repository is run: the `sampletones` command and what it offers, the
tools package behind its developer commands, the scripts under `scripts/`, and the `Makefile`. Read
it before adding a command, a tool, a script or a make target. Which packages may import which is
[package layers](packages.md); the libraries and tools the scripts reach for are
[dependencies](release/dependencies.md).

## Principles

**1. One door.** Everything a person runs by hand is a `sampletones` command with its own parser
and help, always named: `sampletones` alone is `sampletones run`, a file is opened with
`sampletones open <path>`, a recording is converted with `sampletones convert <path>`. A
command's name says what it does, in plain words.

**2. Three kinds of runnable code, told apart by who runs them and what they may import.** The
*application* is what a user installs. A *tool* runs inside the project environment, through
`uv run`: it may import any package, and only the command line reaches it. A *bootstrap script*
runs on the system interpreter, before or beside the environment: it creates the environment,
installs system packages, builds the standalone bundle, cleans the tree, and runs the tests, the
linters and the formatters the environment provides. It imports the standard library and the other
bootstrap modules, nothing else, so it runs on a machine that has Python 3.12 or newer and nothing
more. Importing `scripts/bootstrap/` checks that version before anything else, so an older
interpreter is told the version and where to download it. A bootstrap script installs nothing into
the interpreter it runs on: every package a build installs lands in `.venv-build`, a virtual
environment of its own, and pip is told to refuse any interpreter outside one. System packages are a step of their own, `make system-deps`, the only one that asks for
administrator rights. The import boundary check holds the tree to the rule:
`sampletones_config/boundaries/standalone.yaml` names the scripts, and an import beyond the
standard library and the tree fails the hook.

**3. What earns a place on the command.** An operation is a *user command* when its input and
output are the user's own files and it needs nothing beyond the installed package. It is a
*developer command* when it reads or writes the repository or measures the code on this machine,
so it needs a checkout and the project environment. It is a *bootstrap script* when it must run
without the environment. A test is run by pytest and is never wrapped in a command; a tool the
tests exercise is a function they call.

**4. A tool is a library with a thin face.** The work is a function that takes values and returns
values; the command module parses the arguments, calls it and prints. A command module imports the
standard library, the command type and its constants at module level, and its implementation
inside `run`, so listing the commands loads no tool. A bootstrap script is shaped the same way:
pure functions assemble the commands and take the decisions, `main` wires in the real runner and
the real environment, and the tests call the functions with a runner that records what it was
asked to run, so a build is verified without building.

**5. The import graph is declared once and checked.** `sampletones` is the top of the graph, and
the bootstrap tree is a root of its own under the standard-library rule. [Package layers](packages.md)
holds the graph and its enforcement.

**6. Tests mirror the tree.** `tests/unit/<package>/` mirrors `src/<package>/` and
`tests/unit/scripts/` mirrors `scripts/`. Code and its tests move in one change.

**7. One script per operation, the same on every system.** What differs between systems (the
launcher's name and extension, the icon, the package manager, the compiler flags audio playback
needs) sits behind one `Platform` protocol with an implementation per system, chosen by a factory
from `platform.system()`. A script never branches on the operating system itself, and a system the
project does not build on is refused by name. The Makefile is the developer's index, one line per
target: a target names the script that does the work and passes its flag, or, for `run` and
`calibration`, the `sampletones` command it starts with no options. The two shell files at
the root, `install.sh` and `install.bat`, exist for the double-click path and call the same bundle
script.

**8. A developer command works from what it is given, in every copy of the program.** The wheel
and the bundle carry the tools package, so every developer command exists wherever `sampletones`
is installed, and each one reaches files the same way in all of them:

- *Inputs* arrive on the command line or in a file a run wrote, so a run starts from what the person
  running it has.
- *Outputs* go where `--output` (`-o`) names. A measurement given no `-o` writes a timestamped
  directory under the user's Documents; `codec report` and the sample emitters take `-o` always.
- *The repository* is reached through the checkout guard. A command that reads or writes the
  repository, or needs a development dependency, runs from a checkout; so `driver` and `icons`
  rewrite the files the package ships from a checkout, and a measurement runs anywhere.
- *Package data* is read from the package it ships in, which holds in a checkout, in the wheel and
  in the bundle.

## The commands

`src/sampletones/` is the entry package. `dispatcher.py` builds one parser over the commands and
runs the one named; `commands/` holds one module per command and `commands/registry.py` lists
them. A command is a frozen `Command` (`sampletones_shared/command.py`): its name, one line of
help, the function adding its options to a parser, and the function running it over the parsed
arguments. Each command turns its arguments into a frozen record, field by field, before it works; a
command with actions, such as `codec`, reads the action first and builds the record that action takes.
A command writing files names where they go `--output` (`-o`): a file for `convert`, a directory for
the others. An option naming an input says what it reads, so `--config` is a configuration file
wherever it appears.

| Command | What it does |
|---|---|
| `run [--config FILE]` | Starts the application |
| `open PATH [--config FILE]` | Starts the application with a `.stp` project, a `.stn` reconstruction or an `.ins` library loaded; a recording is refused with the `convert` line to run instead |
| `convert SOURCE... [-o FILE] [--config FILE] [--channels LIST \| --stems FILE]` | Reconstructs recordings into one `.stn` file, or every recording under one directory file by file. `--stems` names a JSON file holding the setup the `.stn` record stores, its entries paired with the sources in order; the pairing is printed before the run, and a missing source, a file other than a recording or a missing stems file is refused first |
| `library [--config FILE]` | Generates the instruction library for a configuration |
| `self-check` | Verifies that the build's imports, bundled resources and configuration files are usable |

`--version` and `--help` are flags of the entry itself. The headless runs behind `convert` and
`library` live in `sampletones_core/headless/`, where the calibration reuses them.

The developer commands, listed by `sampletones_tools/registry.py` and run as
`uv run sampletones <command>` from a checkout:

| Command | What it does |
|---|---|
| `calibration [--config FILE] [-o DIR] [--methods LIST] [--perceptual-exponents LIST] [--temporal-weights LIST] [--channels LIST] [--palette NAME] [--no-open]` | Measures how the program reconstructs the reference sounds under the packaged suite, or the parts of it the options replace, and writes the renders, the report and the page the renders are heard on; `make calibration` runs it with no options; without `-o` the run lands in a timestamped directory under Documents/SampleToNES/calibration |
| `calibration --board RUN [RUN ...] [-o DIR] [--palette NAME] [--no-open]` | Builds one listening page over finished runs, measuring nothing; without `-o` the page lands in a timestamped directory under Documents/SampleToNES/calibration/pages. [Calibration](../tools/calibration.md) explains every use |
| `check <name> [options]` | Holds the tree to one of its checks: `import-boundary`, `language-keys`, `palette-colors`, `rendered-literals`, `shortcut-actions`, `tag-names`, `unused-tags`; each is a pre-commit hook, and [architecture](architecture.md#enforcement) says what each holds. Needs a checkout |
| `btp samples -o DIR`, `ftm samples -o DIR`, `nsf samples -o DIR` | Builds the synthetic corpus and writes it as example files: the arrangement as two Bitphase documents (at its tempo and as a groove), the arrangement as a FamiTracker module, or each sample and the arrangement as `.nsf` programs |
| `compatibility [-o DIR] [--force]` | Archives one document per stored format at the data versions this build writes, into `tests/data/compatibility`, so a later build can open what this one wrote; a version already archived stands as it was written unless `--force` replaces it. Needs a checkout |
| `codec report -o DIR` | Compresses the synthetic corpus under every layer of the codec and writes the report the format's constants are settled from, as CSV and Markdown |
| `codec study [--manifest FILE] [--project FILE]... [--reconstruction PATH]... [-o DIR] [--lengthen SECONDS] [--variants LIST]` | Encodes the projects and stems it is given, or the ones a manifest names, under every candidate change to the codec and writes the sizes, the times, a verdict per candidate and the manifest that repeats the run; without `-o` the run lands under Documents/SampleToNES/compression |
| `driver [-o DIR]` | Assembles the NES player driver with cc65 and prints the layout the build produced; without `-o` it writes the driver the package ships, which needs a checkout |
| `icons [-o DIR]` | Writes the icon suite from the mark, into `-o` or over the icons the package ships. Needs a checkout |
| `nsf render --directory DIR [--tail SECONDS]` | Renders every exported `.nsf` file in the directory to a wave beside it, through ffmpeg's libgme demuxer |

## The tools package

`src/sampletones_tools/` holds every tool the running application does not use, in subpackages by
subject, and `sampletones_tools/registry.py` lists the developer commands they offer.
`sampletones/commands/registry.py` appends them to the user commands, which is the one import of
the tools package; [package layers](packages.md) holds the edge. Two helpers carry out principle 8:

- `sampletones_tools/checkout.py` holds `require_checkout(command)`: the repository root holds
  `pyproject.toml` beside `src/`, or the command exits naming `uv run sampletones <command>` in a
  checkout. `icons` calls it for Pillow, a development dependency, as well as for the repository.
- `package_directory` in `sampletones_shared/paths/package.py` places a package from the import
  system's own record, where PyInstaller unpacks each package's data beside its modules.

A tool that writes a page ships that page's files as they are read. `calibration/board/static/`
holds the markup, the stylesheet and the script, copied out byte for byte, and the builder writes
the palette, the faces and the run's own contents beside them. The stylesheet names color tokens
and the script names no measurement, so a page is edited in place and drawn in the application's
palettes; a test holds every shipped file to reaching nothing beyond the page, which is what lets
one open from a file.

Developer commands are run as `uv run sampletones <command>` from a checkout; the `sampletones`
command `make setup` installs is a wheel and refuses the guarded ones the same way. A command module
imports pillow, NumPy and the like inside `run`, and a test imports the registry in a subprocess and
asserts that only the command, registry and package modules of the tools load and no heavy library
does, since a startup failure in any tool module would break every invocation, the GUI included. A
command reports each refused value on a line of its own: `describe_failure` in
`sampletones_shared/utils/validation.py` renders a validation error the way a person reads it. The
editable install puts `src/` on the path whole, so a checkout
sees the tools package whatever the wheel lists; hatchling's `dev-mode-exact` stays off for that
reason.

## The bootstrap scripts

| Script | Target | What it does |
|---|---|---|
| `bundle.py` | `make build`, `make release` | Creates `.venv-build`, installs the package with the `build` extra, checks the interpreter carries PortAudio (and Tk, for a release), writes the bundle with PyInstaller, runs its self-check, and copies the notices beside a release. Every package the wheel carries brings its data files at its own package path, so the frozen application finds them where an installed one does |
| `setup_environment.py` | `make setup` | Reads the NVIDIA driver, synchronizes the development environment with the matching GPU extra, installs the global `sampletones` command |
| `system_dependencies.py` | `make system-deps` | Installs the system packages: apt on Debian-based Linux, Homebrew on macOS, nothing on Windows |
| `build_environment.py` | CI | Prints the compiler flags a macOS build exports, one `KEY=VALUE` per line |
| `clean.py` | `make clean` | Removes the build outputs, the coverage reports and the bytecode caches |
| `run_tests.py` | `make test`, `make test-docs`, `make benchmarks` | Runs one pass of the tests, named on its command line: `suite`, the covered suite across six workers (`--workers` sets the count); `doctests`; or `benchmarks`, serial and uncovered. Each pass is a target, a pre-push hook and a CI step of its own, so a failure names its pass |
| `lint.py` | `make lint` | Runs mypy over the files `pyproject.toml` configures and pylint over `src/` and `scripts/`; `--mypy` or `--pylint` picks one, and named paths narrow both |
| `formatting.py` | `make format` | Runs isort, then black, over `src/`, `tests/` and `scripts/`, or over the paths named |
| `hooks.py` | `make pre-commit` | Installs the git hooks pre-commit runs at commit and at push |
| `runtime_hooks/release_environment.py` | build input | The PyInstaller runtime hook that gives a release bundle its deployment defaults |
| `verify_version_tag.py` | the release workflow | Holds the release tag to the version `pyproject.toml` records |
| `verify_bundle.py` | the release workflow | Holds the release bundle to its notices, keeps the build tools out of it, and starts its launcher |
| `archive_bundle.py` | the release workflow | Zips the release bundle into `bundles/`, named by the version and the `--label` of the platform |

`scripts/bootstrap/` holds what they share, one fact in one place:

- `layout.py`: the repository root and every path and list a script names: `bin`, `bundles`,
  `.venv-build`, the runtime hook, the notices, the build tools a bundle leaves out, and what
  `make clean` removes.
- `project.py`: what `pyproject.toml` states, read with `tomllib`: the name, the version, the
  entry module, the wheel's packages, and the extras and groups the scripts install, which it
  holds the file to.
- `platforms/`: what differs between systems, behind `Platform`, with `Bundling` holding what a
  bundle takes on a system that builds one.
- `cuda.py`: the NVIDIA driver's CUDA version and the CuPy extra it selects.
- `interpreter.py`, `processes.py`, `passes.py`, `files.py`: the interpreter version check,
  running a command and holding it to success, a run of named passes that reports every failure
  at once, and removing a file or a tree.
- `venv_build.py`, `preflight.py`: the build environment and the installs into it, and the
  preflight of the build interpreter.

Every script's work is a function taking what it reads: the repository root, the platform, and for
a script running commands the runner and the variables. `main` parses the arguments and passes in
the real ones, and the tests pass a temporary repository and a `RecordingRunner`.

## Who governs what

| Concern | Owner |
|---|---|
| Which commands the entry offers | `src/sampletones/commands/registry.py` |
| Which developer commands exist | `src/sampletones_tools/registry.py` |
| Which checks the tree is held to | `src/sampletones_tools/checks/registry.py` |
| Whether a command runs outside a checkout | `src/sampletones_tools/checkout.py` |
| The synthetic corpus the emitters and the integration tests share | `src/sampletones_tools/corpus/` |
| The page a calibration run is listened to on | `src/sampletones_tools/calibration/board/` |
| What a command is | `src/sampletones_shared/command.py` |
| What a bootstrap script may import | `sampletones_config/boundaries/standalone.yaml` |
| What differs between systems | `scripts/bootstrap/platforms/` |
| Where a script finds a path, a notice or a clean target | `scripts/bootstrap/layout.py` |
| What the scripts read from `pyproject.toml` | `scripts/bootstrap/project.py` |
| Where a build installs | `scripts/bootstrap/venv_build.py` |
| What a bundle has to carry before it is built | `scripts/bootstrap/preflight.py` |
| The PyInstaller invocation | `scripts/bundle.py` |
| The test passes and the command each runs | `scripts/run_tests.py` |
| What `make lint` and `make format` sweep | `scripts/lint.py`, `scripts/formatting.py` |
| The GPU extra a machine gets | `scripts/bootstrap/cuda.py` |
| What a release is held to | `scripts/verify_version_tag.py`, `scripts/verify_bundle.py` |
