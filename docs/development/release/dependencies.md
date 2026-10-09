# Dependencies

This document says why each dependency exists and what it needs from the machine. Consult it when adding a dependency, changing the build, or diagnosing an install that fails. `pyproject.toml` states every Python dependency and the version each is held to. This page covers what `pyproject.toml` cannot say: system libraries, build-time tools and the reason each one is there.

Dependencies fall into groups by who needs them: what ships with the application, what only the build needs, and what only developers need. Each section below says which group it belongs to.

## Graphical interface

The interface is built with [DearPyGui](https://github.com/hoffstadt/DearPyGui), a Python wrapper for [Dear ImGui](https://www.dearimgui.com/). It ships with the application.

## Core

The reconstruction engine stands on the usual numerical stack, with `cupy` as an optional GPU backend. The GPU backend is installed as the extra that matches the machine's NVIDIA driver. See [GPU acceleration](../../guide/installation.md#gpu-acceleration) for enabling it. [GPU bundles](#gpu-bundles) says how a standalone executable carries it.

## Serialization

Instruction libraries and reconstructions are serialized with [MessagePack](https://msgpack.org/) (the `msgpack` package). It needs no external compiler or system dependency and installs automatically with the package.

## Audio playback

Playback goes through PortAudio, reached with the `pyaudio` package. PyPI has `pyaudio` wheels for Windows only, so Linux and macOS compile it on install and need the PortAudio headers and library on the machine. `scripts/system_dependencies.py` installs them: the distribution packages through apt on Linux, and PortAudio through Homebrew on macOS.

On macOS the compile architecture is pinned to the machine's own (`ARCHFLAGS`). Homebrew's PortAudio is native to the machine, while the python.org interpreter is universal2, and pinning makes the two agree. `make setup` sets it, and the CI workflows take it from `scripts/build_environment.py`.

## Audio rendering

Audio files are written with libsndfile, reached with the `soundfile` package. Its wheels carry a prebuilt libsndfile for every supported platform, so the encoders come with the package and need nothing installed alongside them.

The application asks the library at runtime which formats it can write, because the codec set varies by platform and packaging. The MP3 encoder, for example, is present only where libsndfile was built with it. The chooser therefore offers the formats the library reports, so what a user is shown describes the machine it runs on.

The writers (`sampletones_core/audio/writers/`) say which sample rates and qualities each format offers. libsndfile takes MP3 quality as a compression level and not a bitrate, and the bitrates a rate can carry narrow as the rate falls. `writers/bitrate.py` therefore maps a level to the bitrate it reaches at each rate.

## File dialogs

Dialogs open through the XDG desktop portal (`org.freedesktop.portal.FileChooser`), reached over D-Bus with the pure-Python `jeepney` package on Linux. The portal lists every offered file type in its selector and reports back the one the user picked, so a save settles its format from the type chosen there. Where no portal answers, `kdialog` and `zenity` take over, and Tk last.

`jeepney` is declared for Linux only, so the modules that speak to the portal are imported only where it is installed. The application probes for it before reaching them, and the root `conftest.py` keeps them out of collection elsewhere, so the Linux runs of the suite cover them.

## Application icon

The icon suite is generated from a mark declared in `assets/icons/mark/config` and committed, so a plain checkout has the icons the application opens its window with. [Assets](../assets.md) describes the maker that writes it.

Pillow rasterizes the suite. It is declared in the `assets` dependency group, which the `dev` group includes. It serves the assets unit alone, which the build environment never installs, and the bundle script passes `--exclude-module PIL` as well. `pygments`, which arrives with `rich`, offers an image formatter that imports Pillow where it is installed, and PyInstaller follows that import into the bundle. The application reads its icons as files, so the exclusion keeps Pillow's extension modules and the imaging libraries that come with them out of every bundle. `scripts/verify_bundle.py` holds the release bundles to it.

## Calibration

The calibration harness scores renders with referees of its own, built on `numpy` and `scipy`. The `calibration` dependency group adds [Zimtohrli](https://github.com/google/zimtohrli), a psychoacoustic model, as a second opinion. PyPI has its wheels for Windows, Intel macOS and x86-64 Linux, and other systems compile it on install. The group stays out of `dev`. `uv sync --group calibration`, with the extras the environment already uses named beside it, installs it. See [Calibration](../../tools/calibration.md).

## NES player driver

Assembling the console player needs `ca65` and `ld65` from [cc65](https://cc65.github.io/). On Debian and Ubuntu that is `sudo apt install cc65`, and a build names the equivalent for whichever system it runs on when the programs are absent. cc65 is a build-time tool for the driver alone. The assembled `driver.bin` is committed, so exporting an NSF needs no assembler ([the console player](../player.md#building-the-driver) says how it is built).

cc65 is distributed under the zlib license. The link line names our own object files and our own `nsf.cfg`, so nothing of cc65's start-up code or libraries reaches the committed image. That keeps the blob entirely ours to ship under the project's MIT license.

### Verifying the driver

[py65](https://github.com/mnaberez/py65) is a 6502 emulator. The console in `sampletones_tools/console/` runs an `.nsf` on it the way an NSF player does, against memory that watches the APU's address range. That lets the suite hold the image to what a correct driver writes ([the console player](../player.md)). The tools package ships with every install, so py65 is a runtime dependency: the wheel names it and the bundles carry it. Its BSD license leaves the project's own terms untouched, and `THIRD-PARTY-LICENSES.txt` has its text.

Listening to a real APU needs [ffmpeg](https://ffmpeg.org/) with the `libgme` demuxer, which is a build option and not a given. `uv run sampletones nsf render` asks the installed ffmpeg which demuxers it has, and names this system's install command before it decodes anything.

CI runs the driver on py65, which arrives with the package's own dependencies, and `scripts/system_dependencies.py` has what building and running the application needs. cc65 and ffmpeg stay on the machine of whoever assembles the driver or renders a wave. A workflow that did either would put them in those scripts. The application itself needs neither: an export is written by the package's own code, from the committed `driver.bin`.

## GPU bundles

A standalone executable built on a machine with an NVIDIA driver carries CuPy and the CUDA libraries. The build asks the same driver detector as `make setup`, and `--gpu 0` opts out. The published bundles are built with it off, and `scripts/verify_bundle.py` holds a release to carrying none of them.

A GPU bundle is a directory. The CUDA libraries would otherwise unpack from a single file on every start.

PyInstaller needs four things to carry a CuPy that computes, and the repository supplies each:

- **CuPy whole.** CuPy imports its submodules by name at run time, so the build collects all of `cupy`, `cupy_backends` and `cupyx`.
- **The hook beside the build** (`scripts/pyinstaller_hooks/hook-cupy.py`). It names the CUDA wheels installed in the build environment as hidden imports, which brings in the hooks that collect their shared libraries. It adds their header directories as data, because CuPy compiles kernels with NVRTC and looks the headers up, and it adds `graphlib`, which a compiled CuPy module imports out of sight of the analysis.
- **The runtime hook** (`scripts/runtime_hooks/cuda_bundle.py`). The CUDA library search walks site-packages and then re-runs `sys.executable` to probe the system. Frozen, that re-runs the application and hangs. The hook makes the bundle the only site-packages, so every library is found inside it.
- **A build environment that matches.** A CPU build excludes the GPU packages by name, so a `.venv-build` left over from a GPU build ships none of them.

The self-check is what proves a bundle. `sampletones self-check --gpu` computes a kernel and a matrix product on the card and holds the answer to NumPy's, and a GPU build runs it before it finishes. Importing CuPy alone passes in a bundle that lost its CUDA libraries.

The CUDA license lets an application distribute these libraries inside itself, on its terms ([third-party notices](../../../THIRD-PARTY-NOTICES.md#gpu-acceleration)). A GPU bundle is for its builder's machine.

## Linux (standalone executable)

Building a standalone executable on Linux needs the PortAudio, Tk and OpenGL/X11 system packages. `make system-deps` installs them (or run `python3 scripts/system_dependencies.py`), and the script has the full list.

PortAudio is required. Tk backs the file dialogs where neither a portal nor a desktop tool answers, and `make release` requires it so the shipped executable stays self-contained.

The executable links against the glibc of the machine that builds it and runs on that version or newer. A redistributable artifact therefore belongs on the oldest Debian or Ubuntu release being supported, so it runs on every newer one.
