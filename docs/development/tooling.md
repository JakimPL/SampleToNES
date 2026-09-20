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

`src/sampletones/` is the entry package. `dispatcher.py` builds one parser over the commands and runs
the one named; `commands/registry.py` lists the user commands, and `sampletones_tools/registry.py`
lists the developer commands appended to them. A command is a frozen `Command`
(`sampletones_shared/command.py`): its name, one line of help, the function adding its options to a
parser, and the function running it over the parsed arguments. `--version` and `--help` are flags of
the entry itself, and `sampletones --help` is the list of what a build offers.

These conventions hold the command surface together. Each command turns its arguments into a frozen
record, field by field, before it works. A command with actions, such as `codec`, reads the action
first and builds the record that action takes. A command writing files names where they go `--output`
(`-o`). An option naming an input says what it reads, so `--config` is a configuration file wherever
it appears. A refused value is reported on a line of its own, through `describe_failure` in
`sampletones_shared/utils/validation.py`.

The headless runs behind `convert` and `library` live in `sampletones_core/headless/`, where the
calibration reuses them.

## The tools package

`src/sampletones_tools/` holds every tool the running application does not use, in subpackages by
subject. Two helpers carry out principle 8:

- `sampletones_tools/checkout.py` holds `require_checkout(command)`: the repository root holds
  `pyproject.toml` beside `src/`, or the command exits naming `uv run sampletones <command>` in a
  checkout. `icons` calls it for Pillow, a development dependency, as well as for the repository.
- `package_directory` in `sampletones_shared/paths/package.py` places a package from the import
  system's own record, where PyInstaller unpacks each package's data beside its modules.

A command module imports pillow, NumPy and the like inside `run`, so listing the commands loads no
tool. A test imports the registry in a subprocess and asserts that only the command, registry and
package modules of the tools load and no heavy library does, since a startup failure in any tool
module would break every invocation, the GUI included.

A tool that writes a page ships that page's files as they are read. `calibration/board/static/`
holds the markup, the stylesheet and the script, copied out byte for byte, and the builder writes
the palette, the faces and the run's own contents beside them. The stylesheet names color tokens
and the script names no measurement, so a page is edited in place and drawn in the application's
palettes; a test holds every shipped file to reaching nothing beyond the page, which is what lets
one open from a file.

The editable install puts `src/` on the path whole, so a checkout sees the tools package whatever the
wheel lists; hatchling's `dev-mode-exact` stays off for that reason.

## The bootstrap scripts

`scripts/` holds one script per operation (principle 7). What they share sits in
`scripts/bootstrap/`, one fact in one place — `layout.py` holds the repository root and every path,
notice and clean target a script names, and `project.py` holds what `pyproject.toml` states, read
with `tomllib`, which it holds the file to.

Every script's work is a function taking what it reads: the repository root, the platform, and for a
script running commands the runner and the variables. `main` parses the arguments and passes in the
real ones, and the tests pass a temporary repository and a `RecordingRunner`, so a build is verified
without building.

The tests are run as named passes — the suite, the doctests, the benchmarks — and each pass is a make
target, a pre-push hook and a CI step of its own, so a failure names its pass.

## Where each fact lives

| Question | Answer |
|---|---|
| Which commands the entry offers | `src/sampletones/commands/registry.py` |
| Which developer commands exist | `src/sampletones_tools/registry.py` |
| Which checks the tree is held to | `src/sampletones_tools/checks/registry.py` |
| The synthetic corpus the emitters and the integration tests share | `src/sampletones_tools/corpus/` |
| Where a script finds a path, a notice or a clean target | `scripts/bootstrap/layout.py` |
| What the scripts read from `pyproject.toml` | `scripts/bootstrap/project.py` |
| What differs between the systems a script runs on | `scripts/bootstrap/platforms/` |
