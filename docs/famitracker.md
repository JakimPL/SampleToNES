# FamiTracker export format

This document is the reference for how SampleToNES writes FamiTracker files. It
describes the two binary formats the `sampletones_core.famitracker` package
produces — the `.fti` instrument file and the `.ftm` module file — and lists the
FamiTracker capacity limits that the project domain model will grow to respect.

The target is **vanilla FamiTracker 0.4.6** (`FILE_VER = 0x0440`). Files written to
this specification load in stock FamiTracker as well as the 0CC, Dn-FamiTracker and
FamiStudio forks. The module is single-chip 2A03: five channels (two pulse, triangle,
noise, DPCM), with the DPCM channel and DPCM sample bank always empty by design.

All multi-byte integers are **little-endian**. Field types below use `uint8`,
`int8`, `uint32`, `int32`; strings are noted per field. Every constant referenced
here has a named counterpart in `sampletones_core/famitracker/constants.py`, and
every block has its own writer function so this specification is readable straight
from the code.

## A. Binary formats

### A.1 `.fti` — instrument file

An `.fti` holds a single 2A03 instrument: its five sequences inline, then an empty
DPCM section. Written by `sampletones_core/famitracker/fti.py`.

| Field | Type | Value |
| --- | --- | --- |
| magic | 3 bytes | `FTI` |
| version | 3 bytes | `2.4` |
| instrument type | `uint8` | `1` (2A03) |
| name length | `uint32` | byte length of the UTF-8 name |
| name | bytes | the name |
| sequence count | `int8` | `5` |
| sequences | — | five sequence records, in order: volume, arpeggio, pitch, hi-pitch, duty |
| DPCM assignment count | `uint32` | `0` |
| DPCM sample count | `uint32` | `0` |

Each **sequence record**:

| Field | Type | Notes |
| --- | --- | --- |
| enabled | `int8` | `1` if the sequence has items, else `0` (and the record ends here) |
| item count | `uint32` | number of items |
| loop point | `int32` | item index to loop from, or `-1` |
| release point | `int32` | item index for note release, or `-1` |
| setting | `uint32` | sequence setting (arpeggio mode etc.); `0` = default |
| items | `int8` × count | one signed byte per tick |

### A.2 `.ftm` — module file

An `.ftm` is a file header followed by a sequence of named, versioned blocks and a
final `END` marker. Written by `sampletones_core/famitracker/ftm.py`, one function
per block.

**File header**

| Field | Type | Value |
| --- | --- | --- |
| magic | 18 bytes | `FamiTracker Module` |
| version | `uint32` | `0x0440` |

**Block header** (precedes every block payload)

| Field | Type | Value |
| --- | --- | --- |
| name | 16 bytes | block name, NUL-padded to 16 bytes |
| version | `int32` | block version |
| size | `int32` | payload byte length |

The payload size is known only after the payload is built, so blocks are buffered
before their header is emitted. After the last block, the file ends with the 3-byte
marker `END`.

**Blocks** (in write order), with their versions:

- **`PARAMS`** (v6): expansion chip `uint8` (`0` = 2A03/none) · channel count `int32`
  (`5`) · machine `int32` (`0` = NTSC, `1` = PAL) · engine speed `int32` (`0` = machine
  default, otherwise a refresh rate in Hz) · vibrato style `int32` · highlight first
  `int32` · highlight second `int32`.
- **`INFO`** (v1): title, author and copyright, each a fixed **32-byte** NUL-padded
  string, in that order.
- **`HEADER`** (v3): track count as `uint8` holding `count − 1`; then each track's
  title as a NUL-terminated string; then, for each channel, a channel id `uint8`
  followed by one effect-column-count `uint8` per track. Channel ids: square1 `0`,
  square2 `1`, triangle `2`, noise `3`, DPCM `4`.
- **`INSTRUMENTS`** (v6): instrument count `int32`; then per instrument: index
  `int32`, type `uint8` (`1` = 2A03), body, name length `int32`, name bytes. The 2A03
  body is: sequence count `int32` (`5`); per sequence an enabled `uint8` and a
  sequence index `uint8`; then the DPCM key-assignment table across the note range,
  all zero here.
- **`SEQUENCES`** (v6): sequence count `int32`. Pass one, per sequence: index `int32`,
  type `int32` (volume `0`, arpeggio `1`, pitch `2`, hi-pitch `3`, duty `4`), item
  count `uint8`, loop point `int32`, then the items `int8` each. Pass two, per
  sequence: release point `int32`, setting `int32`. Instruments reference these
  pooled sequences by index — the module stores each sequence once.
- **`FRAMES`** (v3): per song — frame count `int32`, speed `int32`, tempo `int32`,
  pattern length `int32`, then the order table: for each frame, one pattern index
  `uint8` per channel.
- **`PATTERNS`** (v5): per non-empty pattern — song index `int32`, channel `int32`,
  pattern index `int32`, row-item count `int32`; then per stored row: row number
  `int32`, note `int8`, octave `int8`, instrument `int8`, volume `int8`, then per
  effect column an effect `int8` and a parameter `int8`.
- **`DPCM SAMPLES`** (v1): sample count `uint8` (`0`).
- **`COMMENTS`** (v1): display-on-open flag `int32`, then the comment as a
  NUL-terminated string.

**Pattern cell encoding.** Note: `0` = empty, `1`–`12` = C–B, `13` = release,
`14` = halt (note cut); octave `0`–`7`. Empty instrument `0x40`, empty volume `0x10`,
empty effect `0`. A pitch converts to a cell by `note = pitch % 12 + 1` and
`octave = pitch // 12 − 2`, matching `pitch_to_name` in
`sampletones_core/utils/frequencies.py`.

## B. FamiTracker capacity limits

FamiTracker bounds several quantities that the SampleToNES `Project` currently
leaves looser. The exporter guards these limits and raises when a project exceeds
them, so it never writes a corrupt file. Enforcing them on the domain model — so the
editor prevents reaching an unexportable state — is planned as a follow-up phase.

_This section is completed in Phase 5, once the exporter's guards are in place._
