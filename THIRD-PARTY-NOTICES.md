# Third-party notices

_SampleToNES_ is released under the MIT License (see [`LICENSE`](LICENSE)). That license
covers the _SampleToNES_ source code only. This file records third-party material that
_SampleToNES_ redistributes or depends on.

Two different things are distributed, and they carry different obligations:

| Distribution | What it contains | Obligations |
| --- | --- | --- |
| The PyPI package (`sampletones` wheel and sdist) | _SampleToNES_ code and the bundled fonts. Dependencies are **not** included; `pip`/`uv` fetches them separately. | Fonts only |
| The standalone bundles attached to GitHub Releases | _SampleToNES_ code, the fonts, the Python runtime, and every dependency — including several native libraries | Fonts, plus the third-party terms described below |

The full license text of everything in the standalone bundles is reproduced in
[`THIRD-PARTY-LICENSES.txt`](https://github.com/JakimPL/SampleToNES/blob/main/THIRD-PARTY-LICENSES.txt),
which ships inside each bundle.

## Bundled fonts

The following font files are redistributed inside both the `sampletones` wheel (under
`sampletones_assets/fonts/`) and the standalone bundles. They are **not** covered by the
MIT License and remain under their original licenses. Full license texts ship alongside
them in `sampletones_assets/fonts/LICENSES/`.

| Font | Copyright | License |
| --- | --- | --- |
| Roboto Mono (all weights and italics, including the variable fonts) | Copyright 2015 The Roboto Mono Project Authors | [SIL Open Font License 1.1](https://github.com/JakimPL/SampleToNES/blob/main/src/sampletones_assets/fonts/LICENSES/OFL-1.1.txt) |
| Source Sans 3 (Regular, Italic, Bold) | © 2023 Adobe, with Reserved Font Name "Source" | [SIL Open Font License 1.1](https://github.com/JakimPL/SampleToNES/blob/main/src/sampletones_assets/fonts/LICENSES/OFL-1.1.txt) |
| DejaVu Sans | © 2003 Bitstream, Inc.; Arev glyphs © Tavmjong Bah; DejaVu changes in the public domain | [Bitstream Vera / Arev](https://github.com/JakimPL/SampleToNES/blob/main/src/sampletones_assets/fonts/LICENSES/DejaVu-BitstreamVera.txt) |

The fonts are redistributed unmodified. Reserved Font Names ("Source", "Bitstream", "Vera")
are not used in any SampleToNES component name.

## The PyPI package

_SampleToNES_ does not vendor any dependency source code — every dependency is installed
separately by `pip`/`uv` from PyPI and imported at runtime.

Most dependencies are permissively licensed (MIT, BSD, Apache-2.0, ISC). Two are under the
GNU Lesser General Public License — [Pebble](https://pypi.org/project/Pebble/) (LGPL-3.0,
a direct dependency) and [soxr](https://pypi.org/project/soxr/) (LGPL-2.1-or-later, a
transitive dependency of `librosa`) — and two, `certifi` and `tqdm`, are under MPL-2.0.

All four are used as unmodified, separately installed libraries loaded dynamically at
import time. No LGPL- or MPL-licensed code is copied into the wheel or the sdist, so the
MIT License applies to the PyPI package without further obligation.

## The standalone bundles

The bundles attached to GitHub Releases are produced by
[PyInstaller](https://pyinstaller.org/) and contain the complete dependency set, the
Python runtime, and a number of native libraries. Publishing them makes _SampleToNES_ a
redistributor of all of that material.

Every component's full license text is in `THIRD-PARTY-LICENSES.txt` at the root of each
bundle. The components below are the ones whose licenses ask for more than attribution.

### Copyleft components

| Component | License | How it enters the bundle |
| --- | --- | --- |
| [Pebble](https://pypi.org/project/Pebble/) 5.2.0 | LGPL-3.0 | Python package, direct dependency |
| [libsndfile](https://github.com/libsndfile/libsndfile) 1.2.2 | LGPL-2.1-or-later | prebuilt shared library inside the `soundfile` package |
| [mpg123](https://www.mpg123.de/) | LGPL-2.1-or-later | statically linked inside libsndfile (MP3 decoding) |
| [LAME](https://lame.sourceforge.io/) 3.100 | LGPL-2.0-or-later | statically linked inside libsndfile (MP3 encoding) |
| [libsoxr](https://sourceforge.net/projects/soxr/) | LGPL-2.1-or-later | compiled into the `soxr` extension module |
| libquadmath | LGPL-2.1-or-later | shared library in `numpy.libs/` and `scipy.libs/` |
| libgfortran | GPL-3.0-or-later WITH GCC Runtime Library Exception | shared library in `numpy.libs/` and `scipy.libs/` |
| libgomp | GPL-3.0-or-later WITH GCC Runtime Library Exception | shared library in `scikit_learn.libs/` |
| [PyInstaller](https://pyinstaller.org/) bootloader | GPL-2.0-or-later WITH the PyInstaller bootloader exception | compiled into the launcher executable |
| [certifi](https://pypi.org/project/certifi/) | MPL-2.0 | Python package (via `requests` → `pooch` → `librosa`) |
| [tqdm](https://pypi.org/project/tqdm/) | MPL-2.0 AND MIT | Python package, direct dependency |

libsndfile also statically links FLAC, Ogg, Vorbis and Opus. Those are BSD-3-Clause; their
copyright notices are reproduced in `THIRD-PARTY-LICENSES.txt`.

### GPL components carrying a linking exception

`libgfortran`, `libquadmath` and `libgomp` are GPL-licensed but are distributed with the
[GCC Runtime Library Exception](https://www.gnu.org/licenses/gcc-exception-3.1.html), which
exists precisely so that compiled output does not become GPL-licensed. The PyInstaller
bootloader is GPL-2.0-or-later with
[an exception](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)
permitting its use in bundles of software under any license.

Neither exception places any obligation on _SampleToNES_ beyond reproducing these notices.
No component of these bundles is under the plain GPL.

### MPL-2.0 components

The Mozilla Public License is file-level copyleft: it covers the MPL-licensed files
themselves, not the program that uses them. `certifi` and `tqdm` are included unmodified,
and their source is available upstream or under the offer below.

### Written offer for source code

Complete corresponding source code for every component listed above is available from its
upstream project. If you would prefer to receive it from us, open an issue at
<https://github.com/JakimPL/SampleToNES/issues> or write to <jakimpl@gmail.com>, and we
will supply the source for the exact versions contained in a given bundle, for at least
three years from the date of that release.

### What the bundles do not contain

The published bundles are **CPU-only**. They contain no CuPy, no CUDA runtime, and no
NVIDIA libraries; those are proprietary and are not redistributable under their EULA. GPU
acceleration is available only when _SampleToNES_ is installed from PyPI with the `gpu`
extra, in which case CuPy and the CUDA components are downloaded by the user directly from
their publishers.

## Keeping this file accurate

The inventory above is a snapshot of the pinned dependency set in `pyproject.toml` and
`uv.lock`. When those change, both this file and `THIRD-PARTY-LICENSES.txt` need to be
reviewed before the next release.
