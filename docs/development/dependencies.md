# Dependencies

## Graphical interface

The graphical user interface is implemented with DearPyGui, a Python wrapper for ImGui (https://www.dearimgui.com/).

## Core

The core depends on common Python packages:
* `numpy`
* `scipy`
* `librosa`
* `cupy` (optional; enables the GPU backend, with the build selected for your NVIDIA driver)

See [GPU acceleration](../guide/installation.md#gpu-acceleration) for enabling it.

## Serialization

Instruction libraries and reconstructions are serialized with [MessagePack](https://msgpack.org/) (the `msgpack` package). No external compiler or system dependency is required — it is installed automatically with the package.

## Audio playback

Playback goes through PortAudio, reached with the `pyaudio` package. PyPI carries `pyaudio` wheels for Windows, so Linux and macOS compile it on install and need the PortAudio headers and library on the machine. Linux takes them from the distribution packages listed in `scripts/linux/build/dependencies.sh`; macOS takes them from Homebrew through `scripts/macos/build/dependencies.sh`.

Compiling on macOS also depends on the interpreter's architecture. The python.org installer ships a universal2 build, which compiles extensions for both Apple Silicon and Intel, while Homebrew's `libportaudio` carries the machine's own architecture. Pinning `ARCHFLAGS` to `uname -m` settles it on the native one: `make setup` sets it directly, and the CI workflows take it from `scripts/macos/build/build_env.sh`, which reports it as a `KEY=VALUE` line alongside the PortAudio prefix for a Homebrew installed outside its usual place.

## Audio rendering

Audio files are written with libsndfile, reached with the `soundfile` package. Its wheels carry a
prebuilt libsndfile 1.2.2 for every supported platform, so the encoders come with the package and
need nothing installed alongside them.

Which formats an installation writes is asked of the library at runtime, because libsndfile is built
with a codec set that varies by platform and packaging — the MP3 encoder in particular arrived in
1.2.0 and is present where it was compiled in. The chooser offers the formats the library reports,
so what a user is shown describes the machine it is running on.

| Format | Sample rates | Quality |
| --- | --- | --- |
| WAV | 8000, 16000, 22050, 44100, 48000, 96000, 192000 Hz | 8, 16, 24 or 32-bit PCM, or 32-bit float |
| MP3 | 8000, 16000, 22050, 44100, 48000 Hz | a bitrate from the ladder its MPEG version defines |

The bitrates on offer narrow with the sample rate: up to 320 kbps at 44100 and 48000 Hz, 160 kbps at
16000 and 22050 Hz, and 64 kbps at 8000 Hz. libsndfile takes MP3 quality as a compression level
between 0 and 1 and turns it into a rung on that ladder, so a bitrate is reached through the level
its rate maps it to, measured per rate and held in `sampletones_core/audio/writers/bitrate.py`.

## File dialogs

Dialogs open through the XDG desktop portal (`org.freedesktop.portal.FileChooser`), reached over D-Bus with the pure-Python `jeepney` package on Linux. The portal lists every offered file type in its selector and reports back the one the user picked, which is what lets a save settle its format from the type chosen there. Where no portal answers, `kdialog` and `zenity` take over, and Tk last.

`jeepney` is declared for Linux alone, so the modules that speak to the portal are imported where it is installed: the application probes for it before reaching them, and the root `conftest.py` keeps them out of collection elsewhere, leaving the Linux runs of the suite to cover them.

## Application icon

The icon suite in `src/sampletones_assets/icons` is generated from the mark declared beside it in
`src/sampletones_assets/mark`: `mark.yaml` carries the geometry, colours and rasterization
settings, validated as a `Mark`, and `template.svg` is the vector the rendered geometry fills. The
package writes the whole suite — the vector `sampletones.svg` and the rasters the application
ships, `sampletones.png` and the multi-resolution `sampletones.ico` — and `scripts/assets/icons.py`
points it at the directory the icons are shipped from. Rasterization uses Pillow, declared in the
`assets` dependency group.

The whole suite is committed, so a plain checkout carries the icons the application opens its window
with, and every wheel, bundle and test run finds them where they lie. `make icons` writes them again
from the mark, and the `icons` pre-push hook writes them for a push that touches either directory,
holding the committed files to what the mark describes. CI runs that same hook.

Pillow is a build-time tool, and the bundle scripts pass `--exclude-module PIL` to hold it to that:
`pygments`, which arrives with `rich`, offers an image formatter that imports Pillow where it is
installed, and PyInstaller follows that import into the bundle. The application reads its icons as
files, so the exclusion spares every bundle Pillow's extension modules and the imaging libraries
that come with them. `scripts/ci/checks/bundle.py` holds the release bundles to it.

## NES player driver

The player that runs on the console is 6502 assembly, and `src/sampletones_player/driver` holds it
in three parts: `assembly/` carries the sources, their includes and the linker configuration,
`binary/` carries the assembled `driver.bin`, and `assembler/` carries the Python that turns one
into the other. `make player` runs `scripts/player.py` over that package, so the build behaves the
same on every system the project supports.

Assembling needs `ca65` and `ld65` from [cc65](https://cc65.github.io/) — on Debian and Ubuntu,
`sudo apt install cc65`, and a build names the equivalent for whichever system it runs on when the
programs are absent. cc65 is a build-time tool for the driver alone, which is why it belongs
neither in the requirements a user installs nor in `scripts/linux/build/dependencies.sh`.

The assembled `driver.bin` is committed, so a checkout carries the player and exporting an NSF
needs no assembler. A jump table leads the image, which fixes the addresses an NSF header names
whatever the driver's length, so the exporter states them from `specification/driver.py` and a
build holds the linker's own labels to them before it writes anything. Editing the assembly means
running `make player` again and committing what it writes; the driver's test suite rebuilds the
sources and holds the committed image to them wherever cc65 is installed. The wheel carries the
assembled image alone, which is all an installed copy reads.

cc65 is distributed under the zlib licence, and the driver stays clear of it: the link line names
our own object files and our own `nsf.cfg`, so nothing of cc65's start-up code or libraries reaches
the committed image. That keeps the blob entirely ours to ship under the project's MIT licence.

## Linux (standalone executable)

Building a standalone executable on Linux needs the PortAudio, Tk and OpenGL/X11 system packages. Install them with `make system-deps` (or run `scripts/linux/build/dependencies.sh`), which holds the full list.

PortAudio is required. Tk backs the file dialogs where neither a portal nor a desktop tool answers, and `make release` requires it so the shipped executable stays self-contained.

The executable links against the glibc of the machine that builds it and runs on that version or newer, so a redistributable artifact belongs on the oldest Debian or Ubuntu release being supported.
