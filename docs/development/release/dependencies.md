# Dependencies

## Graphical interface

The graphical user interface is implemented with DearPyGui, a Python wrapper for ImGui (https://www.dearimgui.com/).

## Core

The reconstruction engine stands on the usual numerical stack, with `cupy` as an optional GPU
backend, installed as the extra that matches the machine's NVIDIA driver. `pyproject.toml` states
every dependency and the version each is held to. See
[GPU acceleration](../../guide/installation.md#gpu-acceleration) for enabling it.

## Serialization

Instruction libraries and reconstructions are serialized with [MessagePack](https://msgpack.org/) (the `msgpack` package). No external compiler or system dependency is required — it is installed automatically with the package.

## Audio playback

Playback goes through PortAudio, reached with the `pyaudio` package. PyPI carries `pyaudio` wheels for Windows, so Linux and macOS compile it on install and need the PortAudio headers and library on the machine. `scripts/system_dependencies.py` installs them: the distribution packages through apt on Linux, PortAudio through Homebrew on macOS.

Compiling on macOS also depends on the interpreter's architecture. The python.org installer ships a universal2 build, which compiles extensions for both Apple Silicon and Intel, while Homebrew's `libportaudio` carries the machine's own architecture. Pinning `ARCHFLAGS` to `uname -m` settles it on the native one: `make setup` sets it directly, and the CI workflows take it from `scripts/build_environment.py`, which reports it as a `KEY=VALUE` line alongside the PortAudio prefix for a Homebrew installed outside its usual place.

## Audio rendering

Audio files are written with libsndfile, reached with the `soundfile` package. Its wheels carry a
prebuilt libsndfile 1.2.2 for every supported platform, so the encoders come with the package and
need nothing installed alongside them.

Which formats an installation writes is asked of the library at runtime, because libsndfile is built
with a codec set that varies by platform and packaging — the MP3 encoder in particular arrived in
1.2.0 and is present where it was compiled in. The chooser offers the formats the library reports,
so what a user is shown describes the machine it is running on.

The sample rates and qualities each format offers are stated by the writers,
`sampletones_core/audio/writers/`. libsndfile takes MP3 quality as a compression level rather than a
bitrate, and the bitrates a rate can carry narrow as the rate falls, so a level is mapped to the rung
it reaches per rate in `writers/bitrate.py`.

## File dialogs

Dialogs open through the XDG desktop portal (`org.freedesktop.portal.FileChooser`), reached over D-Bus with the pure-Python `jeepney` package on Linux. The portal lists every offered file type in its selector and reports back the one the user picked, which is what lets a save settle its format from the type chosen there. Where no portal answers, `kdialog` and `zenity` take over, and Tk last.

`jeepney` is declared for Linux alone, so the modules that speak to the portal are imported where it is installed: the application probes for it before reaching them, and the root `conftest.py` keeps them out of collection elsewhere, leaving the Linux runs of the suite to cover them.

## Application icon

The icon suite in `src/sampletones_assets/icons` is generated from the mark declared in
`src/sampletones_tools/assets/mark/config`: `mark.yaml` carries the geometry, colors and rasterization
settings, validated as a `Mark`, and `template.svg` is the vector the rendered geometry fills. The
tools package writes the whole suite — the vector `sampletones.svg` and the rasters the application
ships, `sampletones.png` and the multi-resolution `sampletones.ico` — and `uv run sampletones icons`
points it at the directory the icons are shipped from. Rasterization uses Pillow, declared in the
`assets` dependency group, which the `dev` group includes.

The whole suite is committed, so a plain checkout carries the icons the application opens its window
with, and every wheel, bundle and test run finds them where they lie. `uv run sampletones icons`
writes them again from the mark, and the `icons` pre-push hook writes them for a push that touches
either directory, holding the committed files to what the mark describes. CI runs that same hook.

Pillow is a developer tool the build environment never installs, and the bundle script passes
`--exclude-module PIL` besides, to hold it to that:
`pygments`, which arrives with `rich`, offers an image formatter that imports Pillow where it is
installed, and PyInstaller follows that import into the bundle. The application reads its icons as
files, so the exclusion spares every bundle Pillow's extension modules and the imaging libraries
that come with them. `scripts/verify_bundle.py` holds the release bundles to it.

## Calibration

The calibration harness scores renders with referees of its own, built on `numpy` and `scipy`. The
`calibration` dependency group adds [Zimtohrli](https://github.com/google/zimtohrli), a
psychoacoustic model, as a second opinion. PyPI carries its wheels for Windows, Intel macOS and
x86-64 Linux, and other systems compile it on install. The group stays out of `dev`:
`uv sync --group calibration`, with the extras the environment already uses named beside it,
installs it. See [Calibration](../../tools/calibration.md).

## NES player driver

Assembling the console player needs `ca65` and `ld65` from [cc65](https://cc65.github.io/) — on
Debian and Ubuntu, `sudo apt install cc65` — and a build names the equivalent for whichever system it
runs on when the programs are absent. cc65 is a build-time tool for the driver alone: the assembled
`driver.bin` is committed, so a checkout carries the player and exporting an NSF needs no assembler.
Editing the assembly means running `uv run sampletones driver` again and committing what it writes.

cc65 is distributed under the zlib license, and the driver stays clear of it: the link line names
our own object files and our own `nsf.cfg`, so nothing of cc65's start-up code or libraries reaches
the committed image. That keeps the blob entirely ours to ship under the project's MIT license.

### Verifying the driver

[py65](https://github.com/mnaberez/py65), a 6502 emulator in the `dev` dependency group, executes the
assembled driver against memory that watches the APU's address range, which is what lets the suite
hold the image to what a correct driver writes ([the console player](../player.md)). py65 is a
developer dependency, outside both the wheel and the bundles, and its BSD license leaves the
project's own terms untouched.

Listening to a real APU needs [ffmpeg](https://ffmpeg.org/) carrying the `libgme` demuxer, which is a
build option rather than a given: `uv run sampletones nsf render` asks the installed ffmpeg which
demuxers it holds, and names this system's install command before it decodes anything.

Of the three tools the player needs, py65 is the one CI reaches, since the workflows install the
`dev` group and `scripts/system_dependencies.py` carries what building and running the application
needs. cc65 and ffmpeg stay on the machine of whoever assembles the driver or renders a wave, and a
workflow that did either is what would put them in those scripts. The application itself calls
neither: an export is written by the package's own code, from the committed `driver.bin`.

## Linux (standalone executable)

Building a standalone executable on Linux needs the PortAudio, Tk and OpenGL/X11 system packages. Install them with `make system-deps` (or run `python3 scripts/system_dependencies.py`), which holds the full list.

PortAudio is required. Tk backs the file dialogs where neither a portal nor a desktop tool answers, and `make release` requires it so the shipped executable stays self-contained.

The executable links against the glibc of the machine that builds it and runs on that version or newer, so a redistributable artifact belongs on the oldest Debian or Ubuntu release being supported.
