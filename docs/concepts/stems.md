# Stems reconstruction

This document explains how the four channels are shared out when a reconstruction is built from several
stems. Read it before changing how stems share channels. You can read it without the source code.
[Reconstruction](reconstruction.md) describes the single-sample pipeline it builds on.
[Reconstructions](../formats/reconstructions.md) documents the stored record.
[Stems in the application](../development/application/stems.md) covers what the application does with a
stems reconstruction: the Stems card, an edit and a removal.

A stems reconstruction converts several audio [stems](../glossary.md#stem) at once. Each stem is matched
against the [instruction library](../glossary.md#instruction-library) on its own. Within each
[frame](../glossary.md#frame), the channels are handed to the stems one [pick](../glossary.md#pick) at a
time, following a precedence hierarchy. The result is one reconstruction whose `stems_data` records, per
channel and frame, which stem's stream plays.

The terms [level](../glossary.md#level-stems), [drive](../glossary.md#drive),
[mix](../glossary.md#mix), [column](../glossary.md#column) and [resting](../glossary.md#resting) are
defined in the glossary.

## Principles

### 1. Every conversion is a stems conversion

Below the conversion job there is one pipeline and one entry point. A job names the recordings it mixes,
the stems setup that hands their channels out, and the file it writes. A conversion from a single file is
the job whose setup has one stem over every enabled channel. What the reader chose stays above that line:
the application decides how many jobs a request makes and what setup each carries. A batch is many
single-source jobs and is not a mode of its own.

One pipeline lets a per-source channel set, the drive each channel is pushed at, a count of channels one
source may sound at once and a hierarchy reach every conversion alike. It also keeps the classic run from
becoming a second path that has to be kept in step.

### 2. A stem is matched against its own recording

Every stem is loaded, padded to the longest stem's length, and framed on its own. A stem's picks are
therefore scored against the sound that stem contributes, and the channels it wins carry that recording.
Ownership and content say the same thing: a stem heard on its own plays what was recorded on it.

The whole set of recordings is scaled by one factor drawn from the peak of its sum, which holds the stems
at the balance they were captured in. The working-level coefficient is measured on that sum, exactly as
for a single file. The reconstruction the run assembles is the sum of the stems' approximations. It
approximates the summed recordings because each part approximates its part.

### 3. A drive reaches for a louder instruction

A stem's settings name a drive per channel it holds. `1.00` is the level the library is calibrated to. The
drive belongs to the conversion alone. Every candidate is read at unit drive, so the instruction winning a
frame is the one that sounds it at the drive. A channel pushed harder is answered by louder instructions,
up to the loudest that channel holds. Past that the channel saturates, which is the effect a drive is used
for.

A drive applies to one channel of one stem. Raising it lifts that part of the mix, and the other stems and
the stem's other channels stay where they are. Afterwards a frame sounds the instruction it carries, so
nothing reads the drive once the conversion is done. The instruction is the record of the level the run
reached.

### 4. A stem sounds where its recording sounds

A stem takes a channel in the frames where its own recording reaches a level a channel can render, and
stands aside in the rest. A channel a passing stem leaves free goes to a stem that does sound there, or
rests. That keeps a recording that is quiet through a passage from sounding the passage on the channels it
holds elsewhere.

### 5. One pick at a time, while a pick helps

A pick scores each eligible stem's candidates by the cost of that stem's own frame with the candidate
sounding beside the stem's earlier picks. It uses the same two-stage criterion as the single-sample
pipeline. The best candidate across the active level wins, is added to that stem's mix, and takes the
channel.

Picks continue while a candidate lowers a frame's cost, a stem's count leaves it room, and free channels
remain. A channel no pick took goes, silent, to the first sounding stem in hierarchy order that may still
hold it. Then every held channel is scored once more with its stem's other channels sounding.

Each stem has a mix of its own. That keeps a stem's later picks from re-approximating what its earlier
picks already cover, and it leaves what the other stems sound out of the stem's mix.

### 6. A frame is answered whole

Every channel the setup covers leaves a frame either held by a stem or **resting**. A resting channel
holds its channel's null instruction over a silent frame and records the resting stem id. Instruction
streams, rendered approximations and the per-frame stem record therefore all run parallel to the frames
they describe: frame *i* of a channel is frame *i* of the recording. A frame the decoder settles on a
silent instruction records the resting stem id too, so the id and the silence name the same frames. A
channel that rests through every frame is [standing by](../glossary.md#standing-by) and has no stream at
all.

This is what makes a channel count and a hierarchy usable. Without it, a frame a count left unclaimed
would shorten that channel's streams and carry its later frames early. What the channel plays would drift
out of step with the recording it was matched against.

### 7. Ownership and decoding compose

The assignment answers *which stem owns which channel this frame*. The decoder answers *what that channel
plays across frames*. Each held channel leaves the frame with a column of candidates, its silence among
them, as wide as the configured decoder reads. The decoder chooses one candidate per frame from those
columns, greedily or along the lowest-cost path through the whole lattice. A resting frame reaches the
decoder as a column of one, so a channel a count left free sits in the path as the off state it is.
[Choosing instructions](reconstruction.md#5-choosing-instructions) describes the decoders.

### 8. Levels pick in order, and the mode sets how

The hierarchy groups stem ids into levels that pick in the listed order. In `strict` mode a level uses up
its stems' channel counts before the next level picks. In `round_robin` mode the levels take turns,
granting every level's stems one channel per round, and a run lasts as many rounds as the largest count
among the stems sounding. Both modes hold every stem to the count its own settings name. A stem holding
fewer channels than that count runs out of channels first.

### 9. A level's channel goes to the stem with the most to render

A cost is a fraction of its own recording's energy, so two stems' costs stand on different scales.
Comparing them alone would hand a channel to whichever recording is easiest to approximate. Within a
level, a candidate is therefore ranked by how far it lowers its stem's frame cost, weighted by the energy
behind it. The channel reaches the stem whose sound it covers most. Precedence between levels stays the
hierarchy's, because that is what a reader arranges the levels to say.

### 10. Ties resolve deterministically

Equal candidates go to the stem earlier in level order. Channels of one kind at one drive are scored as
one column and resolve to the lowest free channel of that group. Successive picks over one kind therefore
land on the lowest free channel, and a rerun assigns the same way every time. Two channels of a kind that
a stem drives differently are scored separately, because each renders the recording at its own level.

### 11. The single-sample case stays exact

One stem covering every enabled channel at unit drive, sounding as many channels at once as it has, is the
single-sample reconstruction. Property tests hold the assignment to an independent restatement of the
frame objective that scores every candidate alone. The one pipeline therefore serves the single-sample
case exactly.

### 12. The working level follows the covered channels

The summed recordings are scaled so their typical frame plays at the full-scale RMS level of the quietest
tone channel the setup covers, or of the quietest covered channel when the setup covers no tone channel
(see [the working level](reconstruction.md#34-the-working-level-coefficient)). One channel renders that
level whole, so a run sounding fewer channels targets a level its channels reach. Every setup measures
against the channel a single recording would be answered by.

## The setup and the record

The **setup** is the entries and the precedence hierarchy with its mode. An entry is an id and the
settings its recording is converted with:

- the channels it may occupy,
- which of those it carries toward the divider it really sounds,
- the drive on each channel it holds,
- how many of those channels it may sound at once.

Every per-recording choice is a field on those settings. The list a reader sets a run up in, the entry the
run records and a later reader of that record therefore all say the same thing. The settings check
themselves: a drive for exactly the channels held, each within its bounds, and a count of at least one.
The setup keeps the ids unique and the hierarchy naming every entry exactly once, so an inconsistent setup
can be neither built nor stored.

The setup is built per conversion from the sources and the reader's choices, and it travels with the job.
It is part of the request and not of the standard configuration. A source the reader left holding no
channel takes no part: it reaches neither the recordings nor the entries, and the target stays what the
covered channels can render.

A stem's frame has to reach a floor before it can take a channel: the quietest note any channel renders,
measured against the working level. Below that, the frame has nothing audible to contribute.

The record stored in a reconstruction has the setup the assignment was made under. It also has one source
per entry, naming the recording and the file it was read from, and, per channel, the stem that holds each
frame, parallel to the instruction streams. Every reconstruction has one. Together with the instruction
streams it is the whole of what a `.stn` says. See [Reconstructions](../formats/reconstructions.md).

The assignment is greedy per frame, so which stem owns a channel can change from one frame to the next.
