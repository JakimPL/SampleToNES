# Third-party notices

_SampleToNES_ is released under the MIT License (see [`LICENSE`](LICENSE)). That license
covers the SampleToNES source code only. This file records third-party material that is
either redistributed inside the SampleToNES distribution or required at runtime.

## Bundled fonts

The following font files are redistributed inside the `sampletones` wheel, under
`sampletones_assets/fonts/`. They are **not** covered by the MIT License above and remain
under their original licenses. Full license texts ship alongside them in
`sampletones_assets/fonts/LICENSES/`.

| Font | Copyright | License |
| --- | --- | --- |
| Roboto Mono (all weights and italics, including the variable fonts) | Copyright 2015 The Roboto Mono Project Authors | [SIL Open Font License 1.1](src/sampletones_assets/fonts/LICENSES/OFL-1.1.txt) |
| Source Sans 3 (Regular, Italic, Bold) | © 2023 Adobe, with Reserved Font Name "Source" | [SIL Open Font License 1.1](src/sampletones_assets/fonts/LICENSES/OFL-1.1.txt) |
| DejaVu Sans | © 2003 Bitstream, Inc.; Arev glyphs © Tavmjong Bah; DejaVu changes in the public domain | [Bitstream Vera / Arev](src/sampletones_assets/fonts/LICENSES/DejaVu-BitstreamVera.txt) |

The fonts are redistributed unmodified. Reserved Font Names ("Source", "Bitstream", "Vera")
are not used in any SampleToNES component name.

## Runtime dependencies

SampleToNES does not vendor any dependency source code — every package below is installed
separately by `pip`/`uv` from PyPI and imported dynamically at runtime.

Most dependencies are permissively licensed (MIT, BSD, Apache-2.0, ISC). Two are covered by
the GNU Lesser General Public License:

| Package | License | Relationship |
| --- | --- | --- |
| [Pebble](https://pypi.org/project/Pebble/) | LGPL-3.0 | Direct dependency, imported as an unmodified library |
| [soxr](https://pypi.org/project/soxr/) | LGPL-2.1-or-later | Transitive dependency of `librosa` |

Both are used as unmodified, separately installed libraries loaded dynamically at import
time. The LGPL permits this use by software under a different license, and no LGPL-licensed
code is copied into the SampleToNES distribution, so the MIT License applies to SampleToNES
without further obligation.

`certifi` and `tqdm` are under MPL-2.0, a file-level copyleft that likewise imposes no
obligation on SampleToNES as an unmodified, separately installed dependency.

### Note on standalone executable builds

The PyInstaller build produced by `install.sh` / `install.bat` bundles the dependency set —
including the LGPL libraries above — into a single executable. Building and running that
executable locally carries no obligation. **Redistributing** a prebuilt executable (for
example, attaching it to a GitHub release) is a distribution of the LGPL libraries and
triggers LGPL §4/§6: recipients must be able to relink the work against a modified version
of the LGPL library, which in practice means shipping the corresponding library sources or a
written offer for them alongside the binary.

The published PyPI package is unaffected — it contains no LGPL code.
