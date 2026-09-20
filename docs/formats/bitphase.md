# Bitphase export format

This document is the reference for how _SampleToNES_ writes
[Bitphase](https://github.com/paator/bitphase) files. It describes the two files the
`sampletones_core.formats.bitphase` package produces — the `.btp` document and the
`.json` instrument preset — and the Bitphase capacity limits the exporter respects.
Read it before changing anything under `formats/bitphase/`; the sibling
[FamiTracker export](famitracker.md) document covers the other tracker.

The target is Bitphase's **NES (2A03) chip**: five channels (two squares, triangle,
noise, DPCM), with the DPCM channel always silent by design. Every constant referenced
here has a named counterpart under `sampletones_core/formats/bitphase/specification/`
(grouped by unit: `chip`, `channels`, `instruments`, `patterns`).

Bitphase plays a note by three columns acting together, and that shapes the whole
mapping: an **instrument** supplies the per-tick register values, a **table** supplies
the per-tick pitch movement, and the **note column** supplies the pitch they move
around. A reconstruction's volume and duty envelopes become the instrument, its
arpeggio envelope becomes the table, and its reference pitch becomes the note.

## A. File formats

### A.1 `.btp` — the document

A `.btp` is the document's JSON under gzip — no header and no version field. The
exporter writes it without separator padding and with a fixed gzip timestamp, so
exporting an unchanged document twice yields identical bytes. Written by
`formats/bitphase/btp.py`.

Bitphase's loader reads each field on its own and falls back to a default for any it
misses, so a document that carries every field below loads exactly as it was written.

```
Project    { name, author, songs[], loopPointId, patternOrder[], tables[],
             patternOrderColors{}, instruments[] }
Song       { patterns[], tuningTable[], initialSpeed, defaultPatternLength, chipType,
             chipVariant, chipFrequency, interruptFrequency, a4TuningHz,
             virtualChannelMap{} }
Pattern    { id, length, channels[], patternRows[] }
Channel    { rows[], label, effectColumnCount }
Row        { note: { name, octave }, effects[], instrument, table, volume }
Effect     { effect, delay, parameter, tableIndex }
Table      { id, rows[], loop, name, additive }
Instrument { chipType, name, macros{ field: { values[], loop } }, id }
```

Instruments and tables belong to the **project** rather than to a song, so every song
addresses the same lists. `patternOrder` names the pattern each order position plays,
and `loopPointId` is the order position playback returns to.

**Field names are camelCase.** The Pydantic models under `formats/bitphase/model/`
carry snake_case attributes and serialize through a camelCase alias generator, so the
Python side reads like the rest of the codebase while the file reads like Bitphase's.

**A channel lays out as many effect columns as its widest line carries**, up to four, and
Bitphase holds that count across every pattern the channel appears in. An effect reads
from a table wherever its cell names an index of zero or above, so a cell driven by its
own parameter states `-1`; a cell carrying an empty value counts as naming the first
table, which is why the effect column never writes one.

### A.2 `.json` — the instrument preset

Bitphase's instruments panel saves and loads a single instrument at runtime through a
file picker. The file holds `{ chipType, name, macros }`, indented the way Bitphase
writes its own, so a preset written here reads like one saved from the tracker. Written
by `formats/bitphase/preset.py`. The panel writes the macros into the slot the reader has
selected, which supplies the id and the chip.

A preset carries macros alone, so its pitch movement rides in the `toneAdd` each tick
takes (section C.3) rather than in a table.

## B. The NES instrument

An instrument is a **bag of macros**, one per field whose values it decides, and each
macro is read a value per engine tick while a note sounds. A field the bag leaves out
takes Bitphase's own default, so an instrument states the fields a reconstruction
governs and nothing else. From `formats/bitphase/model/instrument.py` and
`specification/macros.py`, matching Bitphase's `NES_APU_MACRO_FIELDS`:

| Field | Range | Default | Runtime meaning | What the exporter writes |
| --- | --- | --- | --- | --- |
| `volumeOrRate` | 0–15 | 15 | the literal channel volume while `envelope` stays off | the volume envelope, or one full level where the slice leaves its volume to the channel |
| `pulseWidth` | 0–3 | 2 | square duty cycle; on the noise channel, any nonzero value selects the short LFSR | the duty-cycle envelope (squares), the short/long mode (noise); the triangle leaves it out |
| `toneAdd` | −4096–4095 | 0 | period offset added to the period the note resolves to (squares and triangle) | the bend a slice sounds (section C.4), and the contour beside it in a preset |
| `envelope` | bool | `false` | reads `volumeOrRate` as a hardware decay rate | left out, so each value is the volume itself |
| `soundLength` | 0–511 | 0 | length counter in ticks; `0` holds the note | left out, so the volume envelope alone shapes the note |
| `toneAccumulation` | bool | `false` | sums `toneAdd` across ticks | left out, since each value is an absolute offset |
| `retrigger` | bool | `false` | restarts the waveform phase this tick | left out, so the waveform runs continuously |
| `sweep` / `sweepRate` / `sweepShift` | bool / 0–7 / −7–7 | `false` / 0 / 0 | the square channel's hardware sweep | left out |

**Each field runs on a counter of its own.** A macro carries the values one field takes
and the index those values circle from, so a dimension holding one value all through
costs that one value however long the others run. Playback circles from the loop index
once the values run out, which makes a macro standing at index `0` circle whole and one
standing at its last value hold that value. A dimension the reconstruction states a
repeat point for circles from that point; one that plays through states its last index
and rests on the value it ends with — silence where the volume envelope ends on a
note-off item, the channel's own level where the slice holds its volume.

**A hand-written instrument's slices.** Bitphase bakes a channel's registers tick by
tick, so an [instrument](../glossary.md#instrument) written by hand reaches a document
as a slice per channel it sounds on, each reading the dimensions that channel offers
and moving around the pitch it states. The envelopes are one set whatever the channel,
so the slices differ only in what each channel reads of them.

**A held volume.** A slice whose volume envelope carries no item leaves its level to the
channel, so the exporter writes one full `volumeOrRate`. Playback combines that level with
the pattern's volume column through a PT3 volume table, where a full level comes out at
the column's own level, so the slice sounds at whatever level the channel carries — the
same reading FamiTracker gives a disabled volume sequence. A slice describing no frame at
all is what writes a single silent value, the smallest instrument Bitphase plays.

## C. Pitch

### C.1 The tuning table

A song carries a 96-entry `tuningTable`, one channel period per note index, built by
`formats/bitphase/tuning.py` as a port of Bitphase's `generate12TETTuningTable`:

```
frequency = a4TuningHz * 2 ^ ((index - 45) / 12)
period    = round(chipFrequency / 16 / frequency)   clamped to 1..2047
```

Rounding matches JavaScript's `Math.round` (half away from zero on positives), so a
table built here equals the one Bitphase derives from the same settings. The exporter
writes NTSC (1 789 773 Hz) at concert pitch; PAL (1 662 607 Hz) and Dendy
(1 773 448 Hz) are named in `specification/chip.py`.

**A note index is the absolute pitch less 24**, which puts indices 0–95 over pitches
24–119 — the same span the FamiTracker exporter clamps to. A pattern cell stores that
index as a semitone and an octave, which playback resolves back with
`name - 2 + (octave - 1) * 12`.

The triangle channel's period is written from the same table, so a written note sounds
an octave below — the convention SampleToNES and FamiTracker already share.

### C.2 Tables carry the contour

A table holds one semitone offset per tick, and playback adds `rows[position]` to the
channel's note every tick, advancing a step per tick and circling from `loop` once the
steps run out. That is a direct match for a reconstruction's arpeggio envelope in absolute
mode, so the contour crosses over verbatim on the pitched channels, carrying the repeat
point the envelope states. A table whose `additive` flag stands measures each step from
the one before it; a contour states its steps from the note, so the flag stays clear.

A pattern's `table` column names a table by `id + 1`; `0` leaves the attached table
alone and `-1` detaches it.

**Noise** derives its period from the note index rather than from the tuning table:
playback reads `period = 15 - (index mod 16)`. Every period therefore repeats once per
sixteen indices, and the exporter picks a base index far enough below the top of the
table for a whole cycle of offsets to stay in range:

```
base index   = 48 + ((15 - initial_period) mod 16)      lands in 48..63
table offset = (-arpeggio_step) mod 16                  lands in 0..15
```

so `15 - ((base + offset) mod 16)` is the period the reconstruction chose, wrapped into
the sixteen the channel holds.

### C.3 Presets fold the contour into the period

An instrument preset carries no table, so its pitch movement is expressed as the per-tick
`toneAdd` each tick applies to the note's own period, the contour and the bend together.
The offsets are measured against the pitch the slice was reconstructed at, under the
tuning a freshly created Bitphase document plays — NTSC at concert pitch. The noise
channel takes its period from the note, so its preset holds a flat offset.

### C.4 The bend rides the tone offset

A reconstruction states a note and, beside it, the timer steps the frame stands away from
that note — the [bend](../glossary.md#bend) an instruction carries as a fine detune and a
coarse one, sixteen steps to the unit. Bitphase counts a period where SampleToNES counts a
timer, and the two differ by one step throughout the table, so a difference of steps
crosses over unchanged: the bend is the `toneAdd` macro, one value per tick.

| What the engine reads | What it means for the export |
| --- | --- |
| the table moves the note, then the tuning table resolves its period | each tick's offset is measured from the note its own contour step reaches, so a transposed trigger keeps the bend it was written with |
| `toneAdd` is added to that period | the offset is what the reconstruction's two bend dimensions state together (`exporters/bend.py`) |
| `toneAccumulation` stays clear | every value is the whole offset for its tick, rather than a step added to a running one |
| a period of zero silences the channel | an offset is held to what keeps the period within 1–2047, which is `bent_timer` read in periods (`formats/bitphase/pitch.py`) |

The squares and the triangle read the offset; the noise channel takes its period from the
note alone, so a noise slice states no `toneAdd` at all. A slice sounding every tick on
its own note states none either, so a document only pays for the bends it sounds.

## D. Tempo as a groove

A Bitphase song states a **speed** — the engine ticks each row lasts — where a _SampleToNES_
project states a tempo and a speed together. The row rate the pair asks for is fractional at
most tempi, so the exporter carries it as a [groove](../glossary.md#groove): whole tick counts,
one per row of a pattern, averaging out to that rate with the longer rows on the bar and the
beat. `sampletones_core/timing/` builds them and in-app playback reads the same groove, so a
document plays the rows the sequencer played. At 60 Hz, speed 6 and tempo 210, a 16-row
pattern in common time comes to

```
5 4 5 4 5 4 4 4 5 4 4 4 5 4 4 4      69 ticks, a rate of 30/7 per row
```

**The groove reaches the engine as a table.** A speed effect that names a table reads one of
its entries per pattern row, which is what carries a per-row tick count into a song:

| Part | What the exporter writes |
| --- | --- |
| `initialSpeed` | the ticks the pattern's first row lasts |
| The table | one entry per pattern row, `loop = 0`, taking the id above the last slice table |
| The effect | `S` with `delay = 0` and an empty parameter, naming that table |
| Its place | the first row of the DPCM channel, in every pattern |

A speed effect applies from whichever channel carries it, so the groove rides the DPCM channel
this exporter leaves silent and every sounding channel keeps its own effect column free. The table advances an entry per row and resumes from where a trigger placed it, so
triggering it again at each pattern start holds every row on the entry that describes it,
however the order jumps.

**A tempo the speed column states writes neither.** Where every row lasts alike — tempo 150 at
60 Hz, where the rate is the speed itself — `initialSpeed` carries the tempo whole, and the
document holds one table per slice with every effect column empty.

## E. What the exporter builds per scope

A `.btp` holds a whole document, so every scope lands in one file; a preset holds one
instrument, so a reconstruction lands as a set of them beside the name the export was
given, one per slice.

| Scope | `.btp` | `.json` preset |
| --- | --- | --- |
| One channel slice | a playable document holding that instrument | one file |
| A whole reconstruction | a playable document holding every slice | one file per slice, beside the chosen name |
| A project | the song, its samples and its arrangement | — |

**Instrument and reconstruction documents are playable.** Each slice becomes an
instrument and the table that carries its contour, and one pattern triggers every slice
at row 0 on the channel it was reconstructed for, so opening the document and pressing
play sounds the reconstruction. The pattern is sized to cover the longest instrument,
and where one instrument outlasts a single pattern the order gains resting positions
until it has played through.

**A project flattens its order.** A SampleToNES order frame points each channel at its
own pattern, where a Bitphase order position names one pattern spanning every channel.
Each frame therefore becomes a pattern of its own carrying that frame's channels side
by side, with `patternOrder = [0..n-1]`. The arrangement crosses over whole; it simply
shares fewer patterns.

Row cells follow from the columns: an instrument command writes the note from
`initial_pitch + transpose`, the instrument number, the table column and the row's
volume; a note-off writes note name `1`; a blank line leaves every column alone.

**The volume column names silence.** In Bitphase you type `0` to silence a channel and
leave the cell blank to carry its level forward — and the file stores those two as `-1` and
`0`. The volume field is declared `allowZeroValue`, so Bitphase parses a typed `0` to `-1`
and prints a stored `-1` back as `0`, while a stored `0` shows as a blank cell; its engine
reads `-1` as volume zero. So a row asking for silence writes `-1`, a row naming a level
writes it verbatim, and a row with an empty volume cell writes `0` — which is the same cell
you would see in the tracker either way.

## F. Bitphase capacity limits

| Quantity | Bitphase limit | Exporter behavior |
| --- | --- | --- |
| Values per instrument macro | 1–512 | keeps a longer dimension's opening values, and a volume ending in silence keeps that silence as its last |
| Rows per table | unbounded | writes the contour, or the groove, whole |
| Effect columns per channel | 1–4 | one, which the groove trigger takes on the DPCM channel |
| Instruments | the instrument column holds 2 base-36 digits, so 1–1295 | raises past 1295 |
| Tables | the table column holds 1 base-36 digit, so ids 0–34 | raises past 35 tables, one of which a groove takes |
| Note range | the 96-entry tuning table, pitch 24–119 | clamps to the nearest playable note |
| Volume column | `-1` silences (the tracker shows `0`), `0` carries the level forward (shown blank), 1–15 set the level | writes the row's level, and `-1` where a row asks for silence |
| Pattern length (rows) | 1–256 | clamps the preview pattern; a project keeps `rows_per_pattern` |
| Order positions | unbounded | matches |
| Speed | 1–255 | the groove's tick counts, bounded to that range |
| DPCM channel | present | rests, apart from the groove trigger each pattern's first row carries |

Tables and instruments are numbered together — each slice takes one of each — so the
table column is what a wide document reaches first, and the exporter raises rather than
writing a document whose later voices cannot be named. A song whose rows vary spends one
of those ids on its groove, so the slices a document holds are those the table column can
still name.

A macro is the one limit a reconstruction meets by itself: 512 values is about eight and a
half seconds at 60 Hz. Each dimension is counted on its own, so a constant duty or a held
level costs one value, and the contour a table carries keeps its whole length whatever the
macros beside it hold. The rule an envelope meets that limit by is `features/limits.py`,
shared with the FamiTracker export.

## G. What does not cross over

**`ProjectInfo.comment`** has no counterpart in a Bitphase document, which carries a name and
an author only, so the exporter leaves the comment behind.

**A document plays at concert pitch.** `a4TuningHz` and the tuning table are written at
A4 = 440 Hz, so a reconstruction tuned elsewhere sounds a document at the pitch Bitphase
creates one with. The distance is recorded in
[bugs and to-dos](../development/bugs-and-todos.md).

**The fields a reconstruction governs are the three it states.** The hardware envelope,
the length counter, the phase retrigger, the sweep and the tone accumulator each stay at
the default Bitphase gives a field the instrument leaves out, and the DPCM sample fields an
instrument may carry are stored by the tracker rather than played, so the exporter writes
none of them.

`interruptFrequency` carries the reconstruction's own tick rate. Bitphase's settings
panel offers 50 and 60 Hz beside a custom value, and its loader and timeline accept any
rate, so one outside that pair plays correctly.
