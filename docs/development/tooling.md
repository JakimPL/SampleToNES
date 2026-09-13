# Tooling

This document governs the scripts under `scripts/` and the `Makefile`: what runs on the system
interpreter, what runs in the project environment, and the rules each kind holds to. Read it
before adding a script or a make target. Which packages may import which is
[package layers](packages.md); the libraries and tools the scripts reach for are
[dependencies](dependencies.md).

## Principles

**1. Two interpreters, two kinds of script.** A *bootstrap script* runs on the system interpreter,
before or beside the project environment: it creates the environment, installs system packages,
builds the standalone bundle, cleans the tree. It imports the standard library and the other
bootstrap modules, nothing else, so it runs on a machine that has Python and nothing more. A
*tool script* runs inside the project environment, through `uv run`, and imports the project's
packages freely.

**2. A bootstrap script installs nothing into the interpreter it runs on.** Every package a build
installs lands in `.venv-build`, a virtual environment of its own, and pip is told to refuse any
interpreter outside a virtual environment. System packages are a step of their own,
`make system-deps`, and the only one that asks for administrator rights. A release build reaches
neither uv nor the developer's environment, so it runs the same on a clean machine.

**3. One script per operation, the same on every system.** What differs between systems (the
launcher's name and extension, the icon, the package manager, the compiler flags audio playback
needs) sits behind one `Platform` protocol with an implementation per system, chosen by a
factory from `platform.system()`. A script never branches on the operating system itself, and a
system the project does not build on is refused by name.

**4. A script is a library with a thin face.** Pure functions assemble the commands and take the
decisions; `main` parses the arguments and wires in the real runner and the real environment.
Tests call the functions with a runner that records what it was asked to run, so the build is
verified without building.

**5. The Makefile is the developer's index, one line per target.** A target names the script
that does the work and passes its flag. The two shell files at the root, `install.sh` and
`install.bat`, exist for the double-click path and call the same bundle script.

## The bootstrap scripts

| Script | Target | What it does |
|---|---|---|
| `bundle.py` | `make build`, `make release` | Creates `.venv-build`, installs the package with the `build` extra, checks the interpreter carries PortAudio (and Tk, for a release), writes the bundle with PyInstaller, runs its self-check, and copies the notices beside a release |
| `setup_environment.py` | `make setup` | Reads the NVIDIA driver, synchronizes the development environment with the matching GPU extra, writes the icons, installs the global `sampletones` command |
| `system_dependencies.py` | `make system-deps` | Installs the system packages: apt on Debian-based Linux, Homebrew on macOS, nothing on Windows |
| `build_environment.py` | CI | Prints the compiler flags a macOS build exports, one `KEY=VALUE` per line |
| `clean.py` | `make clean` | Removes the build outputs, the coverage reports and the bytecode caches |
| `detect_cuda.py` | via `setup_environment.py` | Maps the driver's CUDA version to the CuPy extra |
| `runtime_hooks/release_environment.py` | build input | The PyInstaller runtime hook that gives a release bundle its deployment defaults |
| `ci/` | the release workflow | The gates a release passes: the tag matches the version, the bundle ships its notices and starts |

`scripts/bootstrap/` holds what they share: the repository root (`repository.py`), the
interpreter version check (`interpreter.py`), running a command and holding it to success
(`processes.py`), the build environment and the installs into it (`venv_build.py`), the
preflight of the build interpreter (`preflight.py`), and the platforms (`platforms/`).

## The tool scripts

`calibration.py`, `compression_study.py`, `nsf_render.py`, `player.py`, `assets/icons.py` and
the checks under `checks/` import the project's packages and run inside its environment, from
the make target that names each. The checks are also pre-commit hooks;
[architecture](architecture.md#enforcement) lists them.

## Who governs what

| Concern | Owner |
|---|---|
| What differs between systems | `scripts/bootstrap/platforms/` |
| Where a build installs | `scripts/bootstrap/venv_build.py` |
| What a bundle has to carry before it is built | `scripts/bootstrap/preflight.py` |
| The PyInstaller invocation | `scripts/bundle.py` |
| The GPU extra a machine gets | `scripts/detect_cuda.py` |
| What a release bundle is held to | `scripts/ci/checks/bundle.py` |
