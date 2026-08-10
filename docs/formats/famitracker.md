# FamiTracker export format

This document is the reference for how _SampleToNES_ writes FamiTracker files. It
describes the two binary formats the `sampletones_core.formats.famitracker` package
produces — the `.fti` instrument file and the `.ftm` module file — and lists the
FamiTracker capacity limits that the project domain model will grow to respect.

The target is **vanilla FamiTracker 0.4.6** (`FILE_VER = 0x0440`). Files written to
this specification load in stock FamiTracker as well as the 0CC, Dn-FamiTracker and
FamiStudio forks. The module is single-chip 2A03: five channels (two pulse, triangle,
noise, DPCM), with the DPCM channel and DPCM sample bank always empty by design.

All multi-byte integers are **little-endian**. Field types below use `uint8`,
`int8`, `uint32`, `int32`; strings are noted per field. Every constant referenced
here has a named counterpart under `sampletones_core/formats/famitracker/specification/`
(grouped by unit: `file`, `blocks`, `channels`, `sequences`, `instruments`,
`patterns`, `parameters`), and every block has its own writer function so this
specification is readable straight from the code.

## A. Binary formats

### A.1 `.fti` — instrument file

An `.fti` holds a single 2A03 instrument: its five sequences inline, then an empty
DPCM section. Written by `sampletones_core/formats/famitracker/instrument.py`.

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
final `END` marker. Written by `sampletones_core/formats/famitracker/module.py`, one function
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
  `int32` · highlight second `int32` · speed split point `int32` (the row where the
  tempo/speed interpretation splits, `speed_split_point`).
- **`INFO`** (v1): title, author and copyright, each a fixed **32-byte** NUL-padded
  string, in that order.
- **`HEADER`** (v3): track count as `uint8` holding `count − 1`; then each track's
  title as a NUL-terminated string; then, for each channel, a channel id `uint8`
  followed by one effect-column count per track, each a `uint8` holding `count − 1`.
  Channel ids: square1 `0`,
  square2 `1`, triangle `2`, noise `3`, DPCM `4`.
- **`INSTRUMENTS`** (v6): instrument count `int32`; then per instrument: index
  `int32`, type `uint8` (`1` = 2A03), body, name length `uint32`, name bytes. The 2A03
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

## B. The 2A03 instrument

Both file formats describe the same instrument model. A 2A03 instrument is a name
plus five **sequences**, one per dimension, advanced one item per engine tick while a
note sounds. The `.fti` file stores the sequences inline; the `.ftm` module pools
them in the `SEQUENCES` block and references them by index, so identical sequences
are stored once.

The five sequence kinds, in slot order (`SequenceKind` in `specification/sequences.py`):

| Slot | Kind | Meaning |
| --- | --- | --- |
| 0 | Volume | output volume per tick, 0–15 |
| 1 | Arpeggio | semitone offsets added to the played note (absolute mode) |
| 2 | Pitch | fine per-tick pitch bend, applied cumulatively |
| 3 | Hi-pitch | coarse pitch bend |
| 4 | Duty / Noise | pulse duty cycle 0–3, or the noise short/long mode |

Each sequence carries:

- **items** — the signed per-tick values (`int8`);
- **loop point** — the item index playback returns to after the last item, or `-1`
  to stop at the end;
- **release point** — the item index playback jumps to when the note is released,
  or `-1` for none;
- **setting** — the sequence mode; for arpeggio, `0` selects absolute (the offsets
  are added to the played note).

**Looping.** A looping instrument sets the loop point to `0` on every populated
sequence, so its envelopes repeat from the start while the note is held; a one-shot
instrument leaves every loop point at `-1`. A sample's `loop` flag drives this when
the sample is exported into a module.

**Equal lengths.** FamiTracker advances each sequence on its own per-tick counter, so
every populated sequence of an instrument carries the same item count and the
dimensions stay in step. The volume envelope arrives one item longer than the others,
carrying a trailing zero that releases the note. A looping instrument therefore keeps
the shortest length, dropping that trailing item so the loop sustains; a one-shot
keeps the longest, each shorter dimension holding its final value through the release
tick. That shared length stays within the 252 items a FamiTracker sequence holds, so a
reconstruction longer than 252 frames — 8.4 s at the default 30 fps — exports its opening
252 frames and logs the shortening. The instruments panel colours a sequence input warning
orange once it passes that length, so the limit is visible before an export.

**How _SampleToNES_ fills an instrument.** Each generator slice of a sample's
reconstruction becomes one instrument, so a sample yields one to four instruments.
The arpeggio sequence carries the reconstruction's pitch contour as signed offsets,
and triggering the instrument at `initial_pitch` replays that contour. Volume, duty
(or noise mode) and any pitch sequences carry across directly. The DPCM
key-assignment table is empty by design.

The offset origin is chosen once, when the reconstruction is built, and stored with it
as that channel's reference pitch (see
[Reconstructions](reconstructions.md#contents)). For the pitched channels
`center_pitch` picks it, taking the midpoint of the contour's `(lowest, highest)`
range; the noise channel takes the first sounding period. Every later export reports
that stored pitch as `initial_pitch` and writes each frame as `pitch − initial_pitch`,
wrapped into the 16 available periods on noise. The offsets straddle zero and stay
compact around one note, and the pattern cell holds the contour's midpoint — a rising
contour prints its middle note and opens below it.

## C. FamiTracker capacity limits

FamiTracker bounds several quantities that the _SampleToNES_ `Project` currently
leaves looser. The exporter guards these limits, so every file it writes loads: it
raises on a project structure FamiTracker has no room for, and shortens an envelope
that outruns a sequence. Enforcing them on the domain model — so the editor prevents
reaching an unexportable state — is planned as a follow-up phase; this table is that
checklist.

| Quantity | FamiTracker limit | Project bound today | Exporter behaviour |
| --- | --- | --- | --- |
| Instruments | 64 total | unbounded (1–4 per sample, so ≈16–64 samples) | raises when the distinct slices exceed 64 |
| Sequences per kind | 128 | unbounded | raises when a kind's pool exceeds 128 |
| Items per sequence | 252 | one item per reconstruction frame, unbounded | keeps the opening 252 items and logs a warning |
| Patterns per channel | 128 (indices 0–127) | pool keyed by arbitrary ints | raises when a pattern index exceeds 127 |
| Order frames | 128 | unbounded | raises when the order exceeds 128 frames |
| Pattern length (rows) | 256 | 1–256 (`rows_per_pattern`) | matches; no guard needed |
| Note range | C-0..B-7 (pitch 24–119) | `initial_pitch` 33–119 + `transpose` −24..+36 can exceed it | clamps to the nearest playable note (fidelity loss at the extremes) |
| Title / author | 32 bytes each | 64 characters | truncates to 32 bytes |
| Comment | free text (COMMENTS block) | 65536 characters | carried in full |
| Tempo / speed | engine-dependent (split at row `speed_split_point`) | tempo 32–255, speed 1–31 | written verbatim from settings |
| DPCM samples | 64 | not modelled | always empty by design |

The exporter also reserves a per-channel empty pattern index (`max used index + 1`)
for order slots the song leaves unset; a channel that already fills indices up to
127 leaves no room for it, which the exporter reports rather than emitting a corrupt
order. When the domain model grows to enforce these limits, the editor can prevent
reaching a state the exporter would reject.
