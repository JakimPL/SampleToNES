# Bitphase export format

This document is the reference for how _SampleToNES_ writes [Bitphase](https://github.com/paator/bitphase)
files: the `.btp` document and the `.json` instrument preset. It also lists the Bitphase capacity limits
the exporter respects. Read it before changing anything under `formats/bitphase/`. The sibling
[FamiTracker export](famitracker.md) document covers the other tracker.

The target is Bitphase's **NES (2A03) chip**: five channels (two squares, triangle, noise, DPCM). The DPCM
channel is always silent. Every constant named here has a counterpart under
`sampletones_core/formats/bitphase/specification/`, grouped by unit (`chip`, `channels`, `instruments`,
`patterns`).

Bitphase plays a note with three columns acting together. An **instrument** supplies the per-tick register
values. A **table** supplies the per-tick pitch movement. The **note column** supplies the pitch they move
around. This shapes the whole mapping: a reconstruction's volume and duty envelopes become the instrument,
its arpeggio envelope becomes the table, and its reference pitch becomes the note.

## A. File formats

### A.1 `.btp` — the document

A `.btp` is the document's JSON under gzip, with no header and no version field. The exporter writes it
without separator padding and with a fixed gzip timestamp, so exporting an unchanged document twice yields
identical bytes.

Bitphase's loader reads each field on its own and falls back to a default for any it misses. A document
with every field below loads exactly as it was written.

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

The project owns the instruments and tables, so every song addresses the same lists. `patternOrder` names
the pattern each order position plays. `loopPointId` is the order position playback returns to.

**Field names are camelCase**, as in Bitphase's own files.

A channel has as many effect columns as its widest row, up to four, and Bitphase gives a channel the same
count in every pattern it appears in. An effect reads its argument from a table whenever `tableIndex` is
zero or above, and from `parameter` otherwise, so an effect driven by its parameter writes `tableIndex`
as `-1`. An empty value counts as naming the first table, and the effect is then dropped.

### A.2 `.json` — the instrument preset

Bitphase's instruments panel saves and loads a single instrument through a file picker. The file holds
`{ chipType, name, macros }`, indented the way Bitphase writes its own, so a preset written here reads
like one saved from the tracker. The panel writes the macros into the instrument slot the reader has
selected, and that slot gives the instrument its id and its chip.

A preset has macros only, so its pitch movement goes in the `toneAdd` each tick takes (section C.3)
instead of a table.

## B. The NES instrument

An instrument is a set of **macros**, one per field, and each macro gives that field a value per engine
tick while a note sounds. A field with no macro takes the default below, so an instrument writes a macro
only for the fields a reconstruction decides. The fields match Bitphase's own:

| Field | Range | Default | Runtime meaning | What the exporter writes |
| --- | --- | --- | --- | --- |
| `volumeOrRate` | 0–15 | 15 | the literal channel volume while `envelope` stays off | the volume envelope, or one full level where the slice leaves its volume to the channel |
| `pulseWidth` | 0–3 | 2 | square duty cycle; on the noise channel, any nonzero value selects the short LFSR | the duty-cycle envelope (squares), the short or long mode (noise); the triangle writes no macro |
| `toneAdd` | −4096–4095 | 0 | period offset added to the period the note resolves to (squares and triangle) | the bend the slice sounds (section C.4), and the contour with it in a preset |
| `envelope` | bool | `false` | reads `volumeOrRate` as a hardware decay rate | no macro, so each value is the volume itself |
| `soundLength` | 0–511 | 0 | length counter in ticks; `0` holds the note | no macro, so the volume envelope alone shapes the note |
| `toneAccumulation` | bool | `false` | sums `toneAdd` across ticks | no macro, so each value is a whole offset |
| `retrigger` | bool | `false` | restarts the waveform phase this tick | no macro, so the waveform runs continuously |
| `sweep` / `sweepRate` / `sweepShift` | bool / 0–7 / −7–7 | `false` / 0 / 0 | the square channel's hardware sweep | no macro, so the sweep stays off |

**Every field has its own counter.** A macro has the values one field takes and the index they repeat
from, and Bitphase advances each macro on its own. A field whose value never changes therefore costs one
value, however long the other fields run.

**Looping.** Playback returns to the macro's `loop` index once the values run out. That is the only mode.
A macro whose `loop` is `0` repeats whole, and one whose `loop` is its last index stays on the last value.
A dimension the reconstruction gives a repeat point repeats from that point. A dimension that plays
through writes its last index, and the value it ends on is what the note rests on: silence where the
volume envelope ends on a note-off item, the channel's own level where the slice leaves the volume
alone.

**A hand-written instrument's slices.** Bitphase bakes a channel's registers tick by tick. An
[instrument](../glossary.md#instrument) written by hand therefore reaches a document as one slice per
channel it sounds on. Each slice reads the dimensions that channel offers and moves around the pitch the
instrument states. The envelopes are one set for every channel, so the slices differ only in what each
channel reads of them.

**A held volume.** A slice whose volume envelope has no item leaves its level to the channel. The exporter
writes one full `volumeOrRate`. Playback combines that level with the pattern's volume column through a
PT3 volume table, where a full level comes out at the column's own level. The slice therefore sounds at
whatever level the channel has, which is how FamiTracker reads a disabled volume sequence. A slice that
describes no frame at all writes a single silent value, the smallest instrument Bitphase plays.

**A table runs beside the macros.** The table advances one step per tick on a counter of its own, so the
contour keeps the length and the repeat point the arpeggio envelope was written at, whatever the macros
beside it do.

## C. Pitch

### C.1 The tuning table

A song has a 96-entry `tuningTable`, one channel period per note index. It is a port of Bitphase's
`generate12TETTuningTable`:

```
frequency = a4TuningHz * 2 ^ ((index - 45) / 12)
period    = round(chipFrequency / 16 / frequency)   clamped to 1..2047
```

Rounding matches JavaScript's `Math.round` (half away from zero on positives), so a table built here
equals the one Bitphase derives from the same settings. The exporter writes NTSC (1 789 773 Hz) at concert
pitch. PAL (1 662 607 Hz) and Dendy (1 773 448 Hz) are named in `specification/chip.py`.

**A note index is the absolute pitch less 24.** Indices 0–95 cover pitches 24–119, the span the FamiTracker
exporter clamps to. A pattern cell stores the index as a semitone and an octave, which playback resolves
back with `name - 2 + (octave - 1) * 12`.

The triangle channel's period comes from the same table, so a written note sounds an octave below.
_SampleToNES_ and FamiTracker share that convention.

### C.2 Tables carry the contour

A table has one semitone offset per tick, and playback adds `rows[position]` to the channel's note every
tick. It repeats from `loop` once the steps run out, by the rule a macro repeats by. That matches a
reconstruction's arpeggio envelope in absolute mode, so the contour crosses over verbatim on the pitched
channels, with the repeat point the envelope was written at. A table whose `additive` flag is set adds
each step to the one before it; a contour measures every step from the note, so the flag stays clear.

A pattern's `table` column names a table by `id + 1`. `0` leaves the attached table alone and `-1`
detaches it.

**Noise** derives its period from the note index, not from the tuning table: playback reads
`period = 15 - (index mod 16)`. Every period therefore repeats once per sixteen indices. The exporter picks
a base index far enough below the top of the table for a whole cycle of offsets to stay in range:

```
base index   = 48 + ((15 - initial_period) mod 16)      lands in 48..63
table offset = (-arpeggio_step) mod 16                  lands in 0..15
```

So `15 - ((base + offset) mod 16)` is the period the reconstruction chose, wrapped into the sixteen the
channel has.

### C.3 Presets fold the contour into the period

An instrument preset has no table, so its pitch movement is the per-tick `toneAdd` each tick applies to
the note's own period. One offset carries the contour and the bend together. The offsets are measured
against the pitch the slice was reconstructed at, under the tuning a freshly created Bitphase document
plays: NTSC at concert pitch. The noise channel takes its period from the note, so a preset for it has a
flat offset.

### C.4 The bend rides the tone offset

A reconstruction says which note a frame plays and how far from that note it sounds, in steps of the
channel's own timer. That distance is the [bend](../glossary.md#bend), written as a fine dimension of one
step per unit and a coarse one of sixteen. Bitphase counts a period where _SampleToNES_ counts a timer,
and the two differ by one step across the table, so a distance in steps crosses over unchanged. The bend
is the `toneAdd` macro, one value per tick.

| What the engine does | What the exporter writes |
| --- | --- |
| moves the note by the table step, then reads that note's period | each value is measured from the note its own contour step reaches, so a transposed trigger keeps its bend |
| adds `toneAdd` to that period | the two bend dimensions added together, one value per tick |
| leaves `toneAccumulation` clear | a whole offset per tick, not a step added to a running one |
| silences a channel whose period reaches zero | an offset bounded to keep the period within 1–2047, the rule the timer follows |

The squares and the triangle read the offset. The noise channel takes its period from the note alone, so
a noise slice writes no `toneAdd`. A slice that sounds every tick on its own note writes none either, so
a document pays only for the bends it sounds.

## D. Tempo as a groove

A Bitphase song has a **speed**, the ticks each row lasts. A _SampleToNES_ project has a tempo and a speed
together. The row rate the pair asks for is fractional at most tempi, so the exporter writes it as a
[groove](../glossary.md#groove): whole tick counts, one per row of a pattern, averaging out to that rate,
with the longer rows on the bar and the beat. In-app playback reads the same groove, so a document plays
the rows the sequencer played. For example, at 60 Hz with speed 6 and tempo 210, a 16-row pattern in
common time comes to:

```
5 4 5 4 5 4 4 4 5 4 4 4 5 4 4 4      69 ticks, a rate of 30/7 per row
```

**The groove reaches the engine as a table.** A speed effect that names a table reads one of its entries
per pattern row, and that carries a per-row tick count into a song:

| Part | What the exporter writes |
| --- | --- |
| `initialSpeed` | the ticks the pattern's first row lasts |
| The table | one entry per pattern row, `loop = 0`, taking the id above the last slice table |
| The effect | `S` with `delay = 0` and an empty parameter, naming that table |
| Its place | the first row of the DPCM channel, in every pattern |

A speed effect applies from whichever channel has it, so the groove rides the DPCM channel, which this
exporter leaves silent. Every sounding channel keeps its own effect column free. The table
advances an entry per row and resumes from where a trigger placed it. Triggering it at each pattern start
therefore holds every row on the entry that describes it, however the order jumps.

**A tempo the speed column can state needs no groove.** Where every row lasts alike, as with tempo 150 at
60 Hz where the rate is the speed itself, `initialSpeed` has the tempo whole. The document then has one
table per slice, and every effect column is empty.

## E. What the exporter builds per scope

A `.btp` is a whole document, so every scope lands in one file. A preset is one instrument, so a
reconstruction lands as a set of presets beside the name the export was given, one per slice.

| Scope | `.btp` | `.json` preset |
| --- | --- | --- |
| One channel slice | a playable document holding that instrument | one file |
| A whole reconstruction | a playable document holding every slice | one file per slice, beside the chosen name |
| A project | the song, its samples and its arrangement | — |

**Instrument and reconstruction documents are playable.** Each slice becomes an instrument plus the table
that carries its contour. One pattern triggers every slice at row 0 on the channel it was reconstructed
for, so opening the document and pressing play sounds the reconstruction. The pattern is sized to cover the
longest instrument. Where an instrument outlasts a single pattern, the order gains resting positions until
it has played through.

**A project flattens its order.** A SampleToNES order frame points each channel at its own pattern, while
a Bitphase order position names one pattern spanning every channel. Each frame therefore becomes a pattern
of its own with that frame's channels side by side, and `patternOrder = [0..n-1]`. The arrangement crosses
over whole and shares fewer patterns.

Row cells follow from the columns. An instrument command writes the note from `initial_pitch + transpose`,
the instrument number, the table column and the row's volume. A note-off writes note name `1`. A blank
line leaves every column alone.

**The volume column names silence.** In Bitphase you type `0` to silence a channel and leave the cell
blank to carry its level forward. The file stores those two as `-1` and `0`. The volume field is declared
`allowZeroValue`, so Bitphase parses a typed `0` to `-1` and prints a stored `-1` back as `0`, and a
stored `0` shows as a blank cell. Its engine reads `-1` as volume zero. A row asking for silence therefore
writes `-1`, a row naming a level writes it verbatim, and a row with an empty volume cell writes `0`. Each
is the same cell you would see in the tracker.

## F. Bitphase capacity limits

| Quantity | Bitphase limit | Exporter behavior |
| --- | --- | --- |
| Values per instrument macro | 1–512 | writes the opening values of a longer dimension, and keeps a volume's closing silence |
| Rows per table | unbounded | writes the contour, or the groove, whole |
| Effect columns per channel | 1–4 | writes one, which the groove trigger takes on the DPCM channel |
| Instruments | the instrument column holds 2 base-36 digits, so 1–1295 | raises past 1295 |
| Tables | the table column holds 1 base-36 digit, so ids 0–34 | raises past 35 tables, one of which a groove takes |
| Note range | the 96-entry tuning table, pitch 24–119 | clamps to the nearest playable note |
| Volume column | `-1` silences (the tracker shows `0`), `0` carries the level forward (shown blank), 1–15 set the level | writes the row's level, and `-1` where a row asks for silence |
| Pattern length (rows) | 1–256 | clamps the preview pattern; a project keeps `rows_per_pattern` |
| Order positions | unbounded | matches |
| Speed | 1–255 | the groove's tick counts, bounded to that range |
| DPCM channel | present | rests, apart from the groove trigger each pattern's first row carries |

A row that names a voice on a channel the voice has no instrument for plays nothing in the song, so the
exporter writes a note cut on it and reports the row by its frame, channel and row. The project export
dialog lists those rows.

Tables and instruments are numbered together, and each slice takes one of each. The table column is
therefore what a wide document reaches first, and the exporter raises an error instead of writing a
document whose later voices cannot be named. A song whose rows vary spends one of those ids on its groove,
so the slices a document holds are those the table column can still name.

**The macro limit is the one a reconstruction meets by itself.** A dimension reaches it at 512 frames,
which is 8.5 s at 60 Hz. Each field is counted on its own, so a flat duty or a held level costs one value,
and the contour the table carries keeps its whole length. A volume dimension keeps its closing silence as
its last value, because the note has to end. [The FamiTracker export](famitracker.md#b-the-2a03-instrument)
meets its own limit by the same rule.

## G. Data without a counterpart

**`ProjectInfo.comment`** has no counterpart in a Bitphase document, which has a name and an author only,
so the exporter leaves the comment out.

**A document is written at concert pitch.** `a4TuningHz` and the tuning table are written at A4 = 440 Hz,
so a reconstruction tuned elsewhere sounds a document at the pitch Bitphase gives a new one. The distance
is recorded in [bugs and to-dos](../development/bugs-and-todos.md).

**A field a reconstruction does not decide gets no macro.** The hardware envelope, the length counter, the
phase retrigger, the sweep and the tone accumulator each take the default in section B. Bitphase also
stores DPCM sample data on an instrument but never plays it, so the exporter writes none of it.

`interruptFrequency` carries the reconstruction's own tick rate. Bitphase's settings panel offers 50 and
60 Hz beside a custom value, and its loader and timeline accept any rate. A rate outside that pair plays
correctly.
