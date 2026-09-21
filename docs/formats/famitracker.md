# FamiTracker export format

This document is the reference for how _SampleToNES_ writes and reads FamiTracker files. Read it when you
write or check an `.fti` instrument file or an `.ftm` module file. It covers the binary layout of both
formats (A), the instrument model (B), what an imported `.fti` gives a voice (C), FamiTracker's capacity
limits (D) and the memory an instrument takes in the NSF driver (E).

The target is **vanilla FamiTracker 0.4.6** (`FILE_VER = 0x0440`). Files written to this specification
load in stock FamiTracker and in the 0CC, Dn-FamiTracker and FamiStudio forks. The module is single-chip
2A03 with five channels: two pulse, triangle, noise and DPCM. The DPCM channel and the DPCM sample bank
are always empty.

All multi-byte integers are **little-endian**. Field types are `uint8`, `int8`, `uint32` and `int32`.
Strings are noted per field. Every constant named here has a counterpart under
`sampletones_core/formats/famitracker/specification/`, grouped by unit (`file`, `blocks`, `channels`,
`sequences`, `instruments`, `patterns`, `parameters`). Every block has its own writer function, so the
code reads as this specification.

## A. Binary formats

### A.1 `.fti` — instrument file

An `.fti` holds a single 2A03 instrument: its five sequences inline, then an empty DPCM section.

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
| setting | `uint32` | sequence setting (arpeggio mode and so on); `0` is the default |
| items | `int8` × count | one signed byte per tick |

### A.2 `.ftm` — module file

An `.ftm` is a file header, then a sequence of named, versioned blocks, then the `END` marker.

**File header**

| Field | Type | Value |
| --- | --- | --- |
| magic | 18 bytes | `FamiTracker Module` |
| version | `uint32` | `0x0440` |

**Block header** (before every block payload)

| Field | Type | Value |
| --- | --- | --- |
| name | 16 bytes | block name, NUL-padded to 16 bytes |
| version | `int32` | block version |
| size | `int32` | payload byte length |

The payload size is known once the payload is built, so each block is buffered before its header is
written. After the last block comes the 3-byte marker `END`.

**Blocks**, in write order:

| Block | Version | Payload |
| --- | --- | --- |
| `PARAMS` | 6 | The parameters table below |
| `INFO` | 1 | Title, author and copyright, each a 32-byte NUL-padded string, in that order |
| `HEADER` | 3 | The header table below |
| `INSTRUMENTS` | 6 | The instruments table below |
| `SEQUENCES` | 6 | The sequences table below |
| `FRAMES` | 3 | The frames table below |
| `PATTERNS` | 5 | The patterns table below |
| `DPCM SAMPLES` | 1 | Sample count `uint8`, always `0` |
| `COMMENTS` | 1 | Display-on-open flag `int32`, then the comment as a NUL-terminated string |

`PARAMS` payload:

| Field | Type | Value |
| --- | --- | --- |
| expansion chip | `uint8` | `0` (2A03, no expansion) |
| channel count | `int32` | `5` |
| machine | `int32` | `0` NTSC, `1` PAL |
| engine speed | `int32` | `0` for the machine's default, otherwise a refresh rate in Hz |
| vibrato style | `int32` | |
| highlight first | `int32` | |
| highlight second | `int32` | |
| speed split point | `int32` | the row where the tempo and speed interpretation splits (`speed_split_point`) |

`HEADER` payload:

| Field | Type | Notes |
| --- | --- | --- |
| track count | `uint8` | the count minus 1 |
| track title, one per track | NUL-terminated string | |
| channel id, one per channel | `uint8` | square1 `0`, square2 `1`, triangle `2`, noise `3`, DPCM `4` |
| effect-column count, one per track after each channel id | `uint8` | the count minus 1 |

`INSTRUMENTS` payload:

| Field | Type | Notes |
| --- | --- | --- |
| instrument count | `int32` | |
| index, per instrument | `int32` | |
| type | `uint8` | `1` (2A03) |
| body | — | the 2A03 body below |
| name length | `uint32` | |
| name | bytes | |

The 2A03 body is the sequence count `int32` (`5`), then per sequence an enabled `uint8` and a sequence
index `uint8`. The DPCM key-assignment table across the note range follows, all zero.

`SEQUENCES` payload:

| Pass | Field | Type | Notes |
| --- | --- | --- | --- |
| | sequence count | `int32` | |
| 1, per sequence | index | `int32` | |
| 1 | type | `int32` | volume `0`, arpeggio `1`, pitch `2`, hi-pitch `3`, duty `4` |
| 1 | item count | `uint8` | |
| 1 | loop point | `int32` | |
| 1 | items | `int8` each | |
| 2, per sequence | release point | `int32` | |
| 2 | setting | `int32` | |

Instruments reference the pooled sequences by index, so the module stores each sequence once.

`FRAMES` payload, per song:

| Field | Type | Notes |
| --- | --- | --- |
| frame count | `int32` | |
| speed | `int32` | |
| tempo | `int32` | |
| pattern length | `int32` | |
| order table | `uint8` | for each frame, one pattern index per channel |

`PATTERNS` payload, per non-empty pattern:

| Field | Type | Notes |
| --- | --- | --- |
| song index | `int32` | |
| channel | `int32` | |
| pattern index | `int32` | |
| row-item count | `int32` | |
| row number | `int32` | starts each stored row |
| note | `int8` | per stored row |
| octave | `int8` | per stored row |
| instrument | `int8` | per stored row |
| volume | `int8` | per stored row |
| effect | `int8` | per stored row, one for each effect column |
| effect parameter | `int8` | per stored row, one for each effect column |

**Pattern cell encoding**

| Field | Values |
| --- | --- |
| note | `0` empty, `1`–`12` C–B, `13` release, `14` halt (note cut) |
| octave | `0`–`7` |
| instrument | `0x40` when empty |
| volume | `0x10` when empty |
| effect | `0` when empty |

A pitch converts to a cell by `note = pitch % 12 + 1` and `octave = pitch // 12 − 2`. This matches
`pitch_to_name` in `sampletones_core/utils/frequencies.py`.

## B. The 2A03 instrument

Both file formats describe the same instrument model. A 2A03 instrument is a name plus five
**sequences**, one per dimension. Each sequence advances one item per engine tick while a note sounds.
The `.fti` file stores the sequences inline. The `.ftm` module pools them in the `SEQUENCES` block and
references them by index, so identical sequences are stored once.

The five sequence kinds, in slot order (`SequenceKind` in `specification/sequences.py`):

| Slot | Kind | Meaning |
| --- | --- | --- |
| 0 | Volume | output volume per tick, 0–15 |
| 1 | Arpeggio | semitone offsets added to the played note (absolute mode) |
| 2 | Pitch | per-tick divider offset, one step per unit |
| 3 | Hi-pitch | per-tick divider offset, sixteen steps per unit |
| 4 | Duty / Noise | pulse duty cycle 0–3, or the noise short/long mode |

Each sequence has:

| Part | Meaning |
| --- | --- |
| items | the signed per-tick values (`int8`) |
| loop point | the item index playback returns to after the last item, or `-1` to stop at the end |
| release point | the item index playback jumps to when the note is released, or `-1` for none |
| setting | the sequence mode; for arpeggio, `0` selects absolute (the offsets are added to the played note) |

**Bend and arpeggio.** FamiTracker walks an instrument's sequences in slot order. An arpeggio in absolute
mode reloads the period from the note before the two bend sequences add to it
(`CSeqInstHandler::ProcessSequence`). While the arpeggio runs, a pitch item is an offset from the note for
that tick, and a hi-pitch item is the same offset counted sixteen dividers at a time. Once the arpeggio
halts, the same items accumulate on the running period.

_SampleToNES_ writes and reads a bend as the per-tick offset. The writer therefore keeps an arpeggio
running for as long as the bend. An instrument with a bend and no arpeggio gets one holding a single zero
at loop point 0. A shorter arpeggio is extended to the bend's length by holding its final note. What one
step is worth follows the note it bends: under a cent at the lowest notes, widening to a whole semitone at
the highest, where the divider grid is already coarser than the note grid.

**Looping.** Each sequence has a loop point: the item it repeats from while a note is held. A sequence
written without one has the loop point `-1` and plays its items once. Every sequence has its own point, so
a two-item duty cycle can circle on its own period beside a longer volume envelope. A point beyond a
sequence's own items repeats its final item, which is the value it would hold anyway.

**Lengths.** FamiTracker advances each sequence on its own per-tick counter. A sequence that reaches its
last item halts, and the value it wrote stays applied. The driver holds that value for as long as the note
sounds (`CSeqInstHandler::UpdateInstrument`). Every dimension therefore keeps the length it was written
at. A two-item volume envelope beside a one-item duty envelope plays exactly as a padded pair would, and
costs less than the padding.

**The release.** A volume envelope whose frames end audible gets one silent item after them, and that item
stops the note. The driver holds a halted sequence's last value for as long as a row keeps the note
sounding, so a volume envelope that ended audible would sound to the end of the song. Every generator
writes the release item, so a volume dimension is one item longer than the frames it describes.

**The item limit.** A FamiTracker sequence holds up to 252 items. Only this writer applies the limit: an
envelope keeps whatever length it was written at until export. A dimension over the limit is written as
its opening items. A volume dimension keeps its release as the last item, because the note has to end, so
the release displaces the last sounding item that would not fit. A reconstruction reaches the limit at 252
frames, since its volume carries the release past them. At the default 30 fps that is 8.4 s. The export
reports what it left out.

**Empty dimensions.** An empty dimension is written as a disabled sequence. This differs from a sequence
with a single zero: a disabled slot leaves that dimension to the channel, while a one-item sequence sets
the value once and holds it. A dimension is empty when the reconstruction records it as one the channel
governs. Clearing the envelope in the instruments panel produces that state (see
[Reconstructions](reconstructions.md)).

**How _SampleToNES_ fills an instrument.** Each channel slice of a sample's reconstruction becomes one
instrument, so a sample yields one to four instruments. A reconstruction has a stream for every channel.
A stream that describes no frame is a channel standing by (see
[Reconstructions](reconstructions.md#contents)). It gets no place in the instrument table, so the
instruments an export writes are the channels that play.

The arpeggio sequence carries the reconstruction's pitch contour as signed offsets, and triggering the
instrument at `initial_pitch` replays that contour. Volume, duty (or noise mode) and the two bend
sequences carry across directly. A conversion that bent no note records both bend dimensions as ones the
channel governs, so they reach the file as disabled slots. The DPCM key-assignment table is always empty.

An [instrument](../glossary.md#instrument) written by hand is one set of envelopes that every channel
reads, as in FamiTracker itself. It becomes a single instrument, however many channels play it. Each
dimension is written at the length it was typed at and has its own loop point, so a tracker that advances
every sequence on its own counter sounds it the way the engine here plays it. Every channel that names the
instrument reaches that one instrument, each against the initial pitch it reads: its note on the tonal
channels, its period on noise.

**Where a row's note comes from.** A voice has a reference, the place where its zero is, and a row has a
step from it. A pattern cell therefore holds `reference + transpose`, kept inside the range a tonal
channel plays and wrapped into the sixteen periods on noise. A sample's reference is the offset origin its
conversion chose. A hand-written instrument's reference is its initial pitch.

The conversion chooses the origin once, when the reconstruction is built, and stores it as that channel's
reference pitch (see [Reconstructions](reconstructions.md#contents)). For the pitched channels
`center_pitch` picks it, as the midpoint of the contour's `(lowest, highest)` range. The noise channel
takes the first sounding period. Every later export reports the stored pitch as `initial_pitch` and writes
each frame as `pitch − initial_pitch`, wrapped into the 16 available periods on noise. The offsets
straddle zero and stay compact around one note. The pattern cell holds the contour's midpoint, so a rising
contour prints its middle note and opens below it.

## C. Reading an instrument file

An `.fti` is read as well as written. **Import instrument...** in the sequencer brings one into the voice
pool as a hand-written [instrument](../glossary.md#instrument). `instrument.py::read_fti` parses the
layout in section A.1, and `voice.py::instrument_to_voice` makes a voice from the 2A03 instrument it
holds.

A voice has all five dimensions, each with the item it repeats from, so they come across as they stand.
The voice takes the name in the file. A file without a name leaves the voice named after the file itself.
The arpeggio is read as offsets from the pitch a hand-written voice rests at, because a tracker
instrument sounds at whatever note a row names it with.

A sequence that loops from one of its items gives that dimension the point. A sequence that halts at its
end leaves the dimension playing its items once, holding the last of them for as long as the note sounds.
A point outside the sequence's items is read as no point.

**Settings the voice does not hold.** A tracker instrument can say more than a voice holds. The import
reports each of these once it lands, so a reader learns what the file carried:

| In the file | In the voice |
| --- | --- |
| a bend outrunning its arpeggio | each item as the offset it says, where the tracker would accumulate it past the arpeggio's last tick (section B) |
| a release point | a note the pattern cuts with a note-off |
| an arpeggio in fixed, relative or scheme mode | absolute offsets |

`bugs-and-todos.md` lists these under **Tracker**.

A sequence with an item outside the range its dimension holds raises `InvalidInstrumentValuesError`. The
file is read before the pool is touched, so a rejected file leaves the project and its history unchanged.

## D. FamiTracker capacity limits

FamiTracker bounds several quantities, and only this writer applies those bounds. A project keeps whatever
a reader wrote, such as an envelope of any length or a pool of any size, and meets a limit when a file is
built. The writer guards each limit, so every file it writes loads. It raises on a project structure
FamiTracker has no room for, and it shortens an envelope that outruns a sequence while keeping the release
that ends its note.

| Quantity | FamiTracker limit | Project bound | Exporter behavior |
| --- | --- | --- | --- |
| Instruments | 64 total | unbounded (1–4 per sample, one per hand-written instrument) | raises when the instruments exceed 64 |
| Sequences per kind | 128 | unbounded | raises when a kind's pool exceeds 128 |
| Items per sequence | 252 | one item per frame, plus the volume's release; unbounded | keeps the opening items, a volume dimension ending at its release, and reports what it left out |
| Patterns per channel | 128 (indices 0–127) | pool keyed by arbitrary ints | raises when a pattern index exceeds 127 |
| Order frames | 128 | unbounded | raises when the order exceeds 128 frames |
| Pattern length (rows) | 256 | 1–256 (`rows_per_pattern`) | matches; no guard needed |
| Note range | C-0..B-7 (pitch 24–119) | a reference of 33–119 plus a transpose reaching either end of that span | clamps to the nearest playable note (fidelity loss at the extremes) |
| Title / author | 32 bytes each | 64 characters | truncates to 32 bytes |
| Comment | free text (COMMENTS block) | 65536 characters | carried in full |
| Tempo / speed | engine-dependent (split at row `speed_split_point`) | tempo 32–255, speed 1–31 | written verbatim from settings |
| DPCM samples | 64 | not modeled | always empty |

The exporter also reserves an empty pattern index per channel (`max used index + 1`) for order slots the
song leaves unset. A channel that already fills indices up to 127 leaves no room for it, and the exporter
reports this instead of writing a corrupt order.

## E. Driver memory footprint

Compiling a module into an NSF lays each instrument out across two regions of the driver's data. An
instrument's sequences size both regions. The application shows the size before an export, so the cost of
a sample is visible in advance.

The **instrument region** holds the instrument list, one pointer per instrument, followed by each
instrument's body: a sequence-enable bitmask, then one pointer per populated sequence. The **sequence
region** holds one chunk per sequence: a four-field header followed by the items.

| Field | Bytes | Region |
| --- | --- | --- |
| instrument list entry | 2 | instrument |
| sequence-enable bitmask | 1 | instrument |
| sequence pointer, per populated sequence | 2 | instrument |
| item count · loop point · release point · setting | 1 each | sequence |
| item, per tick | 1 | sequence |

An instrument with `n` populated sequences carrying `s₁ … sₙ` items therefore occupies `3 + 2n` bytes of
the instrument region and `Σ (4 + sᵢ)` of the sequence region. A dimension the channel leaves unused is
written as a disabled slot, and only populated sequences are charged. A reconstruction that bent no note
charges 3 sequences on the pulse and noise channels (volume, arpeggio, duty) and 2 on triangle. Each bend
an instrument writes adds one more. Each sequence is charged at its own length (section B), so shortening
any one dimension shows in the figure. An instrument tops out at 777 bytes: three sequences at the
252-item limit.

FamiTracker itself prints these two figures while creating an NSF, as `Instruments used: N (X bytes)` and
`Sequences used: M (Y bytes)`. A measurement can be checked against them.

**Version.** The figures are for vanilla FamiTracker 0.4.6, the target named at the top of this document.
The 0CC and Dn-FamiTracker forks open each instrument body with a channel-type byte, so an instrument
costs one byte more there.

**Pooling.** The `SEQUENCES` block stores each distinct sequence once (section A.2), so two instruments
with the same volume envelope pay for that chunk once. A per-instrument or per-sample figure is that
instrument's own cost, so a module total is at most the sum of them. Within one instrument each kind
appears once, so its own sequences are charged once each.

**Length.** A sequence is written at the length it holds (section B), so a figure counts each dimension as
it stands. A loop point on one dimension adds a byte and no padding. The figure for a voice is therefore
what its **Export instrument...** writes.
