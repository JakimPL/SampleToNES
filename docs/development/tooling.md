# Tooling

This document governs how the repository is run: the `sampletones` command and what it offers, the
tools package behind its developer commands, the scripts under `scripts/`, and the `Makefile`. Read
it before adding a command, a tool, a script or a make target. Which packages may import which is
[package layers](packages.md). The libraries and tools the scripts reach for are
[dependencies](release/dependencies.md).

## Principles

**1. One entry.** Everything a person runs by hand is a `sampletones` command with its own parser and
help, always named. `sampletones` alone is `sampletones run`, a file is opened with
`sampletones open <path>`, and a recording is converted with `sampletones convert <path>`. A command's
name says what it does, in plain words.

**2. Runnable code comes in kinds that differ by who runs it and what it may import.**

- The *application* is what a user installs.
- A *tool* runs inside the project environment, through `uv run`. It may import any package, and only the
  command line reaches it.
- A *bootstrap script* runs on the system interpreter, before or beside the environment. It creates the
  environment, installs system packages, builds the standalone bundle, cleans the tree, and runs the
  tests, the linters and the formatters the environment provides.

A bootstrap script imports the standard library and the other bootstrap modules and nothing else, so it
runs on a machine that has Python 3.12 or newer and nothing more. Importing `scripts/bootstrap/` checks
the version before anything else, so an older interpreter is told the version and where to download it.

A bootstrap script installs nothing into the interpreter it runs on. Every package a build installs lands
in `.venv-build`, a virtual environment of its own, and pip is told to refuse any interpreter outside one.
System packages are a step of their own, `make system-deps`, and it is the only step that asks for
administrator rights.

The import boundary check holds the tree to the rule. `sampletones_config/boundaries/standalone.yaml` names
the scripts, and an import beyond the standard library and the tree fails the hook.

**3. What earns a place on the command.** An operation is a *user command* when its input and output are
the user's own files and it needs nothing beyond the installed package. It is a *developer command* when
it reads or writes the repository or measures the code on this machine, so it needs a checkout and the
project environment. It is a *bootstrap script* when it must run without the environment. A test is run by
pytest, and no command wraps it. A tool the tests exercise is a function they call.

**4. A tool is a library with a thin face.** The work is a function that takes values and returns values.
The command module parses the arguments, calls the function and prints. A command module imports the
standard library, the command type and its constants at module level, and its implementation inside `run`,
so listing the commands loads no tool. A bootstrap script has the same shape. Pure functions assemble the
commands and take the decisions, and `main` wires in the real runner and the real environment. The tests
call the functions with a runner that records what it was asked to run, so a build is verified without
building.

**5. The import graph is declared once and checked.** `sampletones` is the top of the graph, and
the bootstrap tree is a root of its own under the standard-library rule. [Package layers](packages.md)
holds the graph and its enforcement.

**6. Tests mirror the tree.** `tests/unit/<package>/` mirrors `src/<package>/` and
`tests/unit/scripts/` mirrors `scripts/`. Code and its tests move in one change.

**7. One script per operation, the same on every system.** What differs between systems sits behind one
`Platform` protocol with an implementation per system, chosen by a factory from `platform.system()`. It
covers the launcher's name and extension, the icon, the package manager, and the compiler flags audio
playback needs. A script never branches on the operating system itself, and a system the project does not
build on is refused by name.

The Makefile is the developer's index, one line per target. A target names the script that does the work
and passes its flag. The `run` and `calibration` targets name the `sampletones` command they start with no
options. `install.sh` and `install.bat` at the root exist for the double-click path and call the same
bundle script.

**8. A developer command works from what it is given, in every copy of the program.** The wheel and the
bundle carry the tools package, so every developer command exists wherever `sampletones` is installed, and
each one reaches files the same way in all of them:

- *Inputs* arrive on the command line or in a file a run wrote, so a run starts from what the person
  running it has.
- *Outputs* go where `--output` (`-o`) names. A measurement given no `-o` writes a timestamped directory
  under the user's Documents. `codec report` and the sample emitters always take `-o`.
- *The repository* is reached through the checkout guard. A command that reads or writes the repository,
  or needs a development dependency, runs from a checkout. `driver` and `icons` rewrite the files the
  package ships from a checkout, and a measurement runs anywhere.
- *Package data* is read from the package it ships in, which holds in a checkout, in the wheel and in the
  bundle.

## The commands

`src/sampletones/` is the entry package. Its dispatcher builds one parser over the commands and runs the
one named. The registries under `commands/` and `sampletones_tools/` list the user commands and the
developer commands. A command is a frozen `Command`: its name, one line of help, the function that adds its
options to a parser, and the function that runs it over the parsed arguments. `--version` and `--help` are
flags of the entry itself, and `sampletones --help` lists what a build offers.

These conventions hold the command surface together:

- Each command turns its arguments into a frozen record, field by field, before it works.
- A command with actions, such as `codec`, reads the action first and builds the record that action takes.
- A command that writes files names where they go `--output` (`-o`).
- An option that names an input says what it reads, so `--config` is a configuration file wherever it
  appears.
- A refused value is reported on a line of its own, through `describe_failure`.

The headless runs behind `convert` and `library` live in `sampletones_core/headless/`, where the
calibration reuses them.

## The tools package

`src/sampletones_tools/` holds every tool the running application does not use, in subpackages by subject.
Two helpers carry out principle 8:

- `sampletones_tools/checkout.py` holds `require_checkout(command)`. It passes when the repository root has
  `pyproject.toml` beside `src/`, and otherwise the command exits and names `uv run sampletones <command>`
  in a checkout. `icons` calls it for Pillow, a development dependency, as well as for the repository.
- `package_directory` in `sampletones_shared/paths/package.py` places a package from the import system's
  own record, where PyInstaller unpacks each package's data beside its modules.

A test guards principle 4. It imports the registry in a subprocess and asserts that only the command,
registry and package modules of the tools load and no heavy library does. A startup failure in any tool
module would break every invocation, the GUI included.

The `icons` command writes the icon suite from the mark declared in `sampletones_tools/assets/mark/config`. `mark.yaml` has the geometry, colors and rasterization settings, validated as a `Mark`, and `template.svg` is the vector the rendered geometry fills. The suite is the vector `sampletones.svg` and the rasters the application ships, `sampletones.png` and the multi-resolution `sampletones.ico`. The command points at the directory the icons ship from. The whole suite is committed, so every wheel, bundle and test run finds the icons where they lie. The `icons` pre-push hook writes them again for a push that touches either directory, which holds the committed files to what the mark describes, and CI runs that same hook.

A tool that writes a page ships that page's files as they are read. `calibration/board/static/` holds the
markup, the stylesheet and the script, copied out byte for byte, and the builder writes the palette, the
faces and the run's own contents beside them. The stylesheet names color tokens and the script names no
measurement, so a page is edited in place and drawn in the application's palettes. A test holds every
shipped file to reaching nothing beyond the page, which lets one open from a file.

## The bootstrap scripts

`scripts/` holds one script per operation (principle 7). What they share sits in `scripts/bootstrap/`, one
fact in one place. `layout.py` holds the repository root and every path, notice and clean target a script
names. `project.py` holds what `pyproject.toml` says, read with `tomllib`, which it holds the file to.

The tests are run as named passes: the suite, the doctests and the benchmarks. Each pass is a make target,
a pre-push hook and a CI step of its own, so a failure names its pass.
