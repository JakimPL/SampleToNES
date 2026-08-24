# FamiTracker export format

This document is the reference for how _SampleToNES_ writes and reads FamiTracker
files. It describes the two binary formats the `sampletones_core.formats.famitracker`
package produces — the `.fti` instrument file and the `.ftm` module file — states what
a voice takes from an `.fti` it reads back, and lists the FamiTracker capacity limits
that the project domain model will grow to respect.

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

**Looping.** Each sequence states the item it repeats from, so a held note sustains from
that item on. A dimension written without one leaves its loop point at `-1` and plays its
items once. Every envelope carries its own point, so a two-item duty cycle circles on its
own period beside a longer volume envelope. A point beyond a sequence's own items repeats
its final item, which is the value it would hold anyway.

**Lengths.** FamiTracker advances each sequence on its own per-tick counter. A sequence
that reaches its last item halts and leaves the value it wrote applied, which the driver
holds for as long as the note sounds (`CSeqInstHandler::UpdateInstrument`). Every
dimension therefore carries the length it was written at: a two-item volume envelope
beside a one-item duty envelope plays exactly as a padded pair would, and costs the
padding less.

Every length stays within the 252 items a FamiTracker sequence holds, so a reconstruction
longer than 252 frames — 8.4 s at the default 30 fps — exports its opening 252 frames and
logs the shortening. The instruments panel colors a sequence input warning orange once it
passes that length, so the limit is visible before an export.

An empty dimension is written as a disabled sequence, which is a different instrument from
one carrying a single zero: the disabled slot leaves that dimension to the channel, while a
one-item sequence sets the value once and holds it. A dimension arrives empty when the
reconstruction records it as one the channel governs — the state clearing the envelope in the
instruments panel puts it in (see [Reconstructions](reconstructions.md)).

**How _SampleToNES_ fills an instrument.** Each channel slice of a sample's
reconstruction becomes one instrument, so a sample yields one to four instruments.
A reconstruction holds a stream for every channel, and one describing no frame is a
channel standing by (see [Reconstructions](reconstructions.md#contents)): it takes no
place in the instrument table, so the instruments an export writes are the channels
that play.
The arpeggio sequence carries the reconstruction's pitch contour as signed offsets,
and triggering the instrument at `initial_pitch` replays that contour. Volume, duty
(or noise mode) and any pitch sequences carry across directly. The DPCM
key-assignment table is empty by design.

An [instrument](../glossary.md#instrument) written by hand is one set of envelopes
every channel reads, which is the instrument model FamiTracker itself uses, so it
becomes a single instrument however many channels play it. Its dimensions are written
at one length, each holding its final value where it is the shorter, so a tracker
advancing every sequence on a counter of its own sounds it the way the engine here
plays it. Every channel that names it reaches that one instrument, each against the
root it reads — its note on the tonal channels, its period on noise.

**Where a row's note comes from.** A voice states where its zero is and a row states
the step from it, so a pattern cell holds `reference + transpose`, held inside the
range a tonal channel plays and wrapped into the sixteen periods on noise. A sample's
reference is the offset origin its conversion chose; a hand-written instrument's is the
root it states.

That origin is chosen once, when the reconstruction is built, and stored with it as
that channel's reference pitch (see [Reconstructions](reconstructions.md#contents)).
For the pitched channels `center_pitch` picks it, taking the midpoint of the contour's
`(lowest, highest)` range; the noise channel takes the first sounding period. Every
later export reports that stored pitch as `initial_pitch` and writes each frame as
`pitch − initial_pitch`, wrapped into the 16 available periods on noise. The offsets
straddle zero and stay compact around one note, and the pattern cell holds the
contour's midpoint — a rising contour prints its middle note and opens below it.

## C. Reading an instrument file

An `.fti` is read as well as written: **Import instrument...** in the sequencer brings
one into the voice pool as a hand-written [instrument](../glossary.md#instrument).
`instrument.py::read_fti` parses the layout in section A.1, and
`voice.py::instrument_to_voice` makes a voice of the 2A03 instrument it holds.

A voice carries three of the five dimensions — volume, arpeggio and duty — each with the
item it repeats from, so those come across as they stand. The voice takes the name the
file states, and a file naming nothing leaves the voice named after the file itself. The
arpeggio is read as offsets from the pitch a hand-written voice rests at, since a tracker
instrument sounds at whatever note a row names it with.

A sequence looping from one of its items gives that dimension the point; one halting at
its end leaves the dimension playing its items once, holding the last of them for as long
as the note sounds. A point outside the items the sequence carries is read as no point.

**What the voice leaves to the file.** A tracker instrument states more than a voice
holds, and each of those is reported once the import lands, so a reader learns what the
file carried (`InstrumentOmission` in `voice.py`):

| Stated in the file | What the voice holds |
| --- | --- |
| a pitch envelope | a note moved in whole semitones, which the arpeggio carries |
| a hi-pitch envelope | the same |
| a release point | a note the pattern cuts with a note-off |
| an arpeggio in fixed, relative or scheme mode | absolute offsets |

Each of these is a dimension the project model will grow to hold; `bugs-and-todos.md`
under **Tracker** owns that list.

A sequence carrying an item outside the range its dimension holds raises
`InvalidInstrumentValuesError`. The file is read before the pool is touched, so a file
the reader cannot take leaves the project as it stood and the history without an entry.

## D. FamiTracker capacity limits

FamiTracker bounds several quantities that the _SampleToNES_ `Project` currently
leaves looser. The exporter guards these limits, so every file it writes loads: it
raises on a project structure FamiTracker has no room for, and shortens an envelope
that outruns a sequence. Enforcing them on the domain model — so the editor prevents
reaching an unexportable state — is planned as a follow-up phase; this table is that
checklist.

| Quantity | FamiTracker limit | Project bound today | Exporter behavior |
| --- | --- | --- | --- |
| Instruments | 64 total | unbounded (1–4 per sample, one per hand-written instrument) | raises when the instruments exceed 64 |
| Sequences per kind | 128 | unbounded | raises when a kind's pool exceeds 128 |
| Items per sequence | 252 | one item per reconstruction frame, unbounded | keeps the opening 252 items and logs a warning |
| Patterns per channel | 128 (indices 0–127) | pool keyed by arbitrary ints | raises when a pattern index exceeds 127 |
| Order frames | 128 | unbounded | raises when the order exceeds 128 frames |
| Pattern length (rows) | 256 | 1–256 (`rows_per_pattern`) | matches; no guard needed |
| Note range | C-0..B-7 (pitch 24–119) | a reference of 33–119 plus a transpose reaching either end of that span | clamps to the nearest playable note (fidelity loss at the extremes) |
| Title / author | 32 bytes each | 64 characters | truncates to 32 bytes |
| Comment | free text (COMMENTS block) | 65536 characters | carried in full |
| Tempo / speed | engine-dependent (split at row `speed_split_point`) | tempo 32–255, speed 1–31 | written verbatim from settings |
| DPCM samples | 64 | not modeled | always empty by design |

The exporter also reserves a per-channel empty pattern index (`max used index + 1`)
for order slots the song leaves unset; a channel that already fills indices up to
127 leaves no room for it, which the exporter reports rather than emitting a corrupt
order. When the domain model grows to enforce these limits, the editor can prevent
reaching a state the exporter would reject.

## E. Driver memory footprint

Compiling a module into an NSF lays each instrument out across two regions of the driver's
data, and an instrument's sequences size both of them. `footprint.py` measures the two, and
`specification/memory.py` names every field the measurement counts. The instruments panel and
the samples context menu display the result, so the cost of a sample is readable before an
export.

The **instrument region** holds the instrument list — one pointer per instrument — followed by
each instrument's body: a sequence-enable bitmask, then one pointer per populated sequence. The
**sequence region** holds one chunk per sequence: a four-field header followed by the items.

| Field | Bytes | Region |
| --- | --- | --- |
| instrument list entry | 2 | instrument |
| sequence-enable bitmask | 1 | instrument |
| sequence pointer, per populated sequence | 2 | instrument |
| item count · loop point · release point · setting | 1 each | sequence |
| item, per tick | 1 | sequence |

An instrument with `n` populated sequences carrying `s₁ … sₙ` items therefore occupies
`3 + 2n` bytes of the instrument region and `Σ (4 + sᵢ)` of the sequence region. A dimension the
channel leaves unused is written as a disabled slot, and the populated sequences alone are
charged: `n` is 3 on the pulse and noise channels (volume, arpeggio, duty) and 2 on triangle.
Each sequence is charged at its own length (section B), so shortening any one dimension shows
in the figure, and an instrument tops out at 777 bytes — three sequences at the 252-item limit.

These two figures are the ones FamiTracker itself prints while creating an NSF —
`Instruments used: N (X bytes)` and `Sequences used: M (Y bytes)` — which is how a measurement
is held against the tracker.

**Version.** The figures are vanilla FamiTracker 0.4.6, the target section A names. The 0CC and
Dn-FamiTracker forks open each instrument body with a channel-type byte, so an instrument costs
one byte more there.

**Pooling narrows a module's total.** The `SEQUENCES` block stores each distinct sequence once
(section A.2), so a module holding two instruments with the same volume envelope pays for that
chunk once. A per-instrument or per-sample figure states that instrument's own cost, and a
module total is therefore at most the sum of them. Within one instrument each kind appears
once, so its own sequences are charged once each.

**Every dimension is charged at its own length.** A sequence is written at the length it holds
(section B), so a figure counts each dimension as it stands and the loop point one of them
carries adds a byte, not a padding. What a voice is measured at is therefore what its
**Export instrument...** writes.
