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
Song       { patterns[], tuningTable[], initialSpeed, chipType, chipVariant,
             chipFrequency, interruptFrequency, a4TuningHz, virtualChannelMap{} }
Pattern    { id, length, channels[], patternRows[] }
Channel    { rows[], label }
Row        { note: { name, octave }, effects[], instrument, table, volume }
Table      { id, rows[], loop, name }
Instrument { id, chipType, rows[], loop, name }
```

Instruments and tables belong to the **project** rather than to a song, so every song
addresses the same lists. `patternOrder` names the pattern each order position plays,
and `loopPointId` is the order position playback returns to.

**Field names are camelCase.** The Pydantic models under `formats/bitphase/model/`
carry snake_case attributes and serialize through a camelCase alias generator, so the
Python side reads like the rest of the codebase while the file reads like Bitphase's.

### A.2 `.json` — the instrument preset

Bitphase's instruments panel saves and loads a single instrument at runtime through a
file picker. The file holds `{ chipType, name, loop, rows }`, indented the way Bitphase
writes its own, so a preset written here reads like one saved from the tracker. Written
by `formats/bitphase/preset.py`.

A preset carries rows alone, so its pitch movement rides in each row's `toneAdd`
(section C.3) rather than in a table.

## B. The NES instrument

An instrument advances **one row per engine tick** while a note sounds, so a row
carries every register value the channel takes for that tick. From
`formats/bitphase/model/instrument.py`, matching Bitphase's `NesInstrumentRow`:

| Field | Range | Runtime meaning | What the exporter writes |
| --- | --- | --- | --- |
| `pulseWidth` | 0–3 | square duty cycle; on the noise channel, any nonzero value selects the short LFSR | the duty-cycle envelope item (squares), the short/long mode (noise), a flat value (triangle) |
| `volumeOrRate` | 0–15 | the literal channel volume while `envelope` stays off | the volume envelope item |
| `envelope` | bool | reads `volumeOrRate` as a hardware decay rate | `false`, so each item is the volume itself |
| `soundLength` | 0–511 | length counter in ticks; `0` holds the note | `0`, so the volume envelope alone shapes the note |
| `toneAdd` | −4096–4095 | period offset added to the tuning-table period (squares and triangle) | `0` in a document, the pitch contour in a preset |
| `toneAccumulation` | bool | sums `toneAdd` across ticks | `false`, since each item is an absolute offset |
| `retrigger` | bool | restarts the waveform phase this tick | `false`, so the waveform runs continuously |
| `sweep` / `sweepRate` / `sweepShift` | bool / 0–7 / −7–7 | the square channel's hardware sweep | disabled |

**Looping.** Playback returns to the instrument's `loop` row once it runs off the end,
which is the only mode there is. A looping slice therefore sets `loop = 0` so its
envelopes repeat from the start while the note is held; a one-shot sets
`loop = len - 1`, and since the volume envelope ends on a note-off item, the
instrument rests in silence once it has played through. A sample's `loop` flag drives
this, the same flag the FamiTracker exporter reads.

**Equal lengths.** Instrument rows and table rows advance on independent per-tick
counters, so they share a length and a loop point and stay in step for as long as the
note sounds. `equalize_lengths` in `exporters/lengths.py` supplies that shared length —
the same rule the FamiTracker exporter applies, with the item limit left unbounded
here (section D).

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
channel's note every tick. That is a direct match for a reconstruction's arpeggio
envelope in absolute mode, so the contour crosses over verbatim on the pitched
channels.

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

An instrument preset carries no table, so its pitch movement is expressed as the
per-tick `toneAdd` each row applies to the note's own period. The offsets are measured
against the pitch the slice was reconstructed at, under the tuning a freshly created
Bitphase document plays — NTSC at concert pitch. The noise channel takes its period
from the note, so its preset rows hold a flat offset.

## D. What the exporter builds per scope

A `.btp` holds a whole document, so every scope lands in one file; a preset holds one
instrument, so a reconstruction lands as a set of them beside the name the export was
given, one per slice.

| Scope | `.btp` | `.json` preset |
| --- | --- | --- |
| One generator slice | a playable document holding that instrument | one file |
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

## E. Bitphase capacity limits

| Quantity | Bitphase limit | Exporter behaviour |
| --- | --- | --- |
| Items per instrument row list | unbounded | writes the envelope whole |
| Rows per table | unbounded | writes the contour whole |
| Instruments | the instrument column holds 2 base-36 digits, so 1–1295 | raises past 1295 |
| Tables | the table column holds 1 base-36 digit, so ids 0–34 | raises past 35 tables |
| Note range | the 96-entry tuning table, pitch 24–119 | clamps to the nearest playable note |
| Pattern length (rows) | 1–256 | clamps the preview pattern; a project keeps `rows_per_pattern` |
| Order positions | unbounded | matches |
| Speed | 1–255 | written verbatim from settings |
| DPCM channel | present | emitted empty |

Tables and instruments are numbered together — each slice takes one of each — so the
table column is what a wide document reaches first: 35 slices fit, and the exporter
raises rather than writing a document whose later voices cannot be named.

## F. What does not cross over

Three things the SampleToNES model holds have no counterpart in a Bitphase document,
and the exporter leaves them behind:

- **`ProjectInfo.comment`** — a Bitphase project carries a name and an author only.
- **`ProjectSettings.tempo`** — Bitphase's engine is speed-only, so `initialSpeed`
  carries `speed` and the tempo is left to the tick rate.
- **A volume column of `0`** — Bitphase reads it as "leave the volume alone", so a row
  that asks for silence through the volume column alone reaches playback unchanged.

`interruptFrequency` carries the reconstruction's own tick rate. Bitphase's settings
panel offers 50 and 60 Hz, and its loader and timeline accept any value, so a rate
outside that pair plays correctly while leaving that one selector unmatched.
