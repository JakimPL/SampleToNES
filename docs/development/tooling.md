# Tooling

This document governs how the repository is run: the `sampletones` command and what it offers,
the scripts under `scripts/`, and the `Makefile`. Read it before adding a command, a script or a
make target. Which packages may import which is [package layers](packages.md); the libraries and
tools the scripts reach for are [dependencies](dependencies.md).

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
bootstrap modules, nothing else, so it runs on a machine that has Python and nothing more, and it
installs nothing into the interpreter it runs on: every package a build installs lands in
`.venv-build`, a virtual environment of its own, and pip is told to refuse any interpreter outside
one. System packages are a step of their own, `make system-deps`, the only one that asks for
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
target: a target names the script that does the work and passes its flag. The two shell files at
the root, `install.sh` and `install.bat`, exist for the double-click path and call the same bundle
script.

## The commands

`src/sampletones/` is the entry package. `dispatcher.py` builds one parser over the commands and
runs the one named; `commands/` holds one module per command and `commands/registry.py` lists
them. A command is a frozen `Command` (`sampletones_shared/command.py`): its name, one line of
help, the function adding its options to a parser, and the function running it over the parsed
arguments. Each command turns its arguments into a frozen record, field by field, before it works.

| Command | What it does |
|---|---|
| `run [--config FILE]` | Starts the application |
| `open PATH [--config FILE]` | Starts the application with a `.stp` project, a `.stn` reconstruction or an `.ins` library loaded; a recording is refused with the `convert` line to run instead |
| `convert SOURCE... [-o FILE] [--config FILE] [--channels LIST \| --stems FILE]` | Reconstructs recordings into one `.stn` file, or every recording under one directory file by file. `--stems` names a JSON file holding the setup the `.stn` record stores, its entries paired with the sources in order; the pairing is printed before the run |
| `library [--config FILE]` | Generates the instruction library for a configuration |
| `self-check` | Verifies that the build's imports, bundled resources and configuration files are usable |

`--version` and `--help` are flags of the entry itself. The headless runs behind `convert` and
`library` live in `sampletones_core/headless/`, where the calibration reuses them. Developer
commands join the registry as the tools they run move into their own package.

## The bootstrap scripts

| Script | Target | What it does |
|---|---|---|
| `bundle.py` | `make build`, `make release` | Creates `.venv-build`, installs the package with the `build` extra, checks the interpreter carries PortAudio (and Tk, for a release), writes the bundle with PyInstaller, runs its self-check, and copies the notices beside a release |
| `setup_environment.py` | `make setup` | Reads the NVIDIA driver, synchronizes the development environment with the matching GPU extra, writes the icons, installs the global `sampletones` command |
| `system_dependencies.py` | `make system-deps` | Installs the system packages: apt on Debian-based Linux, Homebrew on macOS, nothing on Windows |
| `build_environment.py` | CI | Prints the compiler flags a macOS build exports, one `KEY=VALUE` per line |
| `clean.py` | `make clean` | Removes the build outputs, the coverage reports and the bytecode caches |
| `run_tests.py` | `make test`, `make benchmarks` | Runs the doctests, the covered suite across six workers, and the benchmarks, every pass whatever the earlier ones reported; `--only` picks one pass and `--workers` sets the count |
| `lint.py` | `make lint` | Runs mypy over the files `pyproject.toml` configures and pylint over `src/` and `scripts/`; `--mypy` or `--pylint` picks one, and named paths narrow both |
| `formatting.py` | `make format` | Runs isort, then black, over `src/`, `tests/` and `scripts/`, or over the paths named |
| `hooks.py` | `make pre-commit` | Installs the git hooks pre-commit runs at commit and at push |
| `detect_cuda.py` | via `setup_environment.py` | Maps the driver's CUDA version to the CuPy extra |
| `runtime_hooks/release_environment.py` | build input | The PyInstaller runtime hook that gives a release bundle its deployment defaults |
| `ci/` | the release workflow | The gates a release passes: the tag matches the version, the bundle ships its notices and starts |

`scripts/bootstrap/` holds what they share: the repository root (`repository.py`), the
interpreter version check (`interpreter.py`), running a command and holding it to success
(`processes.py`), a run of named passes that reports every failure at once (`passes.py`), the
build environment and the installs into it (`venv_build.py`), the preflight of the build
interpreter (`preflight.py`), and the platforms (`platforms/`).

## The tool scripts

`calibration.py`, `compression_study.py`, `nsf_render.py`, `player.py`, `assets/icons.py` and
the checks under `checks/` import the project's packages and run inside its environment, from
the make target that names each. The checks are also pre-commit hooks;
[architecture](architecture.md#enforcement) lists them.

## Who governs what

| Concern | Owner |
|---|---|
| Which commands the entry offers | `src/sampletones/commands/registry.py` |
| What a command is | `src/sampletones_shared/command.py` |
| What a bootstrap script may import | `sampletones_config/boundaries/standalone.yaml` |
| What differs between systems | `scripts/bootstrap/platforms/` |
| Where a build installs | `scripts/bootstrap/venv_build.py` |
| What a bundle has to carry before it is built | `scripts/bootstrap/preflight.py` |
| The PyInstaller invocation | `scripts/bundle.py` |
| The passes `make test` runs, and their order | `scripts/run_tests.py` |
| What `make lint` and `make format` sweep | `scripts/lint.py`, `scripts/formatting.py` |
| The GPU extra a machine gets | `scripts/detect_cuda.py` |
| What a release bundle is held to | `scripts/ci/checks/bundle.py` |
