# Stems reconstruction

This document explains how the four channels are shared out when a reconstruction
is built from several stems. You can read it without reading the source code. The
single-sample pipeline it builds on is [Reconstruction](reconstruction.md), and the
stored record is [Reconstructions](../formats/reconstructions.md). What the
application does with a stems reconstruction — the Stems card, an edit and a removal
— is [Stems in the application](../development/application/stems.md).

A stems reconstruction converts several audio [stems](../glossary.md#stem) at once. Each
stem is matched against the [instruction library](../glossary.md#instruction-library) on
its own; within each [frame](../glossary.md#frame), the channels are handed to the stems
one pick at a time, following a precedence hierarchy. The result is one reconstruction
whose `stems_data` records, per channel and frame, which stem's stream plays.

## Principles

### 1. Every conversion is a stems conversion

Below the conversion job there is one pipeline and one entry point. A job names
the recordings it mixes, the stems setup that hands their channels out, and the
file it writes; a conversion from a single file is the job whose setup holds one
stem over every enabled channel. What the reader chose stays above that line:
the application decides how many jobs a request makes and what setup each
carries, and a batch is many single-source jobs rather than a mode of its own.

This is what lets a per-source channel set, the drive each channel is pushed at,
a count of channels one source may sound at once and a hierarchy reach every
conversion alike, and what keeps the classic run from being a second path that
has to be kept in step.

### 2. A stem is matched against its own recording

Every stem is loaded, padded to the longest stem's length, and framed on its own,
so a stem's picks are scored against the sound that stem contributes and the
channels it wins carry that recording. Ownership and content then say the same
thing: a stem heard on its own plays what was recorded on it.

The mix keeps the two jobs it answers: the whole set is scaled by one factor drawn
from the peak of its sum, which holds the stems at the balance they were captured
in, and the working-level coefficient is measured on that mix, exactly as for a
single file. The reconstruction the run assembles is the sum of the stems'
approximations, which approximates the mix because each part approximates its part.

### 3. A drive reaches for a louder instruction

A stem's settings name a drive per channel it holds, `1.00` standing at the level
the library is calibrated to. The drive belongs to the conversion alone: every
candidate is read at unit drive, so the instruction winning a frame is the one
sounding it at the drive, and a channel pushed harder is answered by louder
instructions up to the loudest that channel holds. Past that the channel
saturates, which is the effect a drive is reached for. A drive answers for one
channel of one stem, so raising it lifts that part of the mix while the other
stems and the stem's other channels stand where they are. What a frame sounds
afterwards is the instruction it carries, so the drive is a record of the level
the run reached at.

### 4. A stem sounds where its recording sounds

A stem takes a channel in the frames its own recording reaches a level a channel
can render, and stands aside in the rest. A channel a passing stem leaves free goes
to a stem that does sound there, or rests. This is what keeps a recording quiet
through a passage from sounding that passage on the channels it holds elsewhere.

### 5. One pick at a time, while a pick helps

A pick scores each eligible stem's candidates by the cost of that stem's own frame
with the candidate sounding beside the stem's earlier picks, with the same two-stage
criterion the single-sample pipeline uses, takes the winning offer
across the active level, adds it to that stem's mix, and consumes the channel. Picks
continue while an offer lowers a frame's cost and counts and free channels remain. A
channel no pick took goes, silent, to the first sounding stem in hierarchy order that
may still hold it, and every held channel is then scored once more with its stem's other
channels sounding. Each stem carrying a mix of its own is what keeps its later picks
from re-approximating what its earlier picks already cover, while leaving what the
other stems sound out of it.

### 6. A frame is answered whole

Every channel the setup covers leaves a frame either held by a stem or **resting**. A
resting channel holds its channel's null instruction over a silent frame and
records the resting stem id, so instruction streams, rendered approximations and
the per-frame stem record all run parallel to the frames they describe: frame
*i* of a channel is frame *i* of the recording. A frame the decoder settles on a
silent instruction records the resting stem id too, so the id and the silence name
the same frames. A channel that rests through every frame stands by instead, carrying
no stream at all.

This is what makes a channel count and a hierarchy usable. Without it, a frame a
count left unclaimed would shorten that channel's streams and carry its later
frames early, so what the channel plays would drift out of step with the
recording it was matched against.

### 7. Ownership and decoding compose

The assignment answers *which stem owns which channel this frame*; the decoder
answers *what that channel plays across frames*. Each held channel leaves the frame
with a column of candidates, its silence among them, as wide as the configured
decoder reads, and the decoder chooses one candidate per frame from those columns —
greedily, or along the lowest-cost path through the whole lattice. A resting frame reaches the
decoder as a column of one, so a channel a count left free sits in the path as the
off state it is. See [Reconstruction §5](reconstruction.md) for the decoders
themselves.

### 8. Precedence orders, mode alternates

The hierarchy groups stem ids into levels that pick in the listed order. In
`strict` mode a level exhausts its stems' channel counts before the next level
picks; in `round_robin` mode the levels take turns, granting every level's stems
one channel per round, and a run lasts as many rounds as the largest count among
the stems sounding. Both modes hold every stem to the count its own settings
name, and a stem holding fewer channels than that runs out of channels first.

### 9. A level's channel goes to the stem with the most to render

A cost is a fraction of its own recording's energy, so two stems' costs stand on
different scales and comparing them alone would hand a channel to whichever
recording is easiest to approximate. Within a level, an offer is therefore ranked
by how far its head lowers the stem's frame cost, weighted by the energy behind it,
so the channel reaches the stem whose sound it covers most. Precedence between levels
stays the hierarchy's, which is what a reader arranges the levels to say.

### 10. Ties resolve deterministically

Equal offers go to the stem earlier in level order. Channels of one kind at one
drive are scored as one column and resolve to the lowest free channel of that
group, so successive picks over one kind land on the lowest free channel and a
rerun assigns the same way every time. Two channels of a kind a stem drives
differently answer for themselves, since each renders the recording at its own
level.

### 11. The single-sample case stays exact

One stem covering every enabled channel at unit drive, sounding as many channels
at once as it holds, is the single-sample reconstruction. Property tests hold the
assignment against an independent restatement of the frame objective that scores
every candidate alone —
identical choices, instructions, costs and contributions — so the one pipeline serves
the single-sample case exactly as it stands.

### 12. The working level follows the covered channels

The mix is scaled so its typical frame plays at the full-scale RMS level of the
quietest tone channel the setup covers, or of the quietest covered channel when it
covers no tone channel (see [Reconstruction §3.4](reconstruction.md)). One channel
renders that level whole, so a run sounding fewer channels targets a level its
channels reach, and
every setup measures against the channel a single recording would be answered by.

## Mechanics

A conversion request becomes jobs in one of three shapes: the recordings it was given mixed
into one job, each gathered recording given a job of its own, or a folder scanned into one
job per audio file. The jobs run across a pool of worker processes.

The **setup** is the entries and the precedence hierarchy with its mode. An entry is an id
and the settings its recording is converted with: the channels it may occupy, which of those
it carries toward the divider it really sounds, the drive on each channel it holds, and how
many of them it may sound at once. Every per-recording choice is a field on those settings,
which is what lets the list a reader sets a run up in, the entry the run records, and a later
reader of that record all say the same thing. The settings check themselves — a drive for
exactly the channels held, each within its bounds, and a count of at least one — and the
setup keeps the ids unique and the hierarchy naming every entry exactly once, so an
inconsistent setup can be neither built nor stored.

The setup is built per conversion from the sources and the reader's choices, and travels with
the job. It is part of the request rather than of the standard configuration. A source the
reader left holding no channel takes no part: it reaches neither the recordings nor the
entries, and the target stays what the covered channels can render.

**Drive enters where the level matters.** The library serves its candidates as they stand,
and the matcher scales them by the drive the column is scored at — powers and variances by
its square, waveforms and means by the drive itself — so a run at unit drive costs exactly
what a run without drives costs. Rendering then uses the same drive, read off the recorded
entry, and a frame no recording holds renders at unit drive. Scoring and rendering therefore
stand at one level: the instruction a frame records is the one chosen for the sound that
frame makes, whenever that sound is read.

A stem's frame has to reach a floor before it can take a channel — the quietest note any
channel renders, measured against the working level. Below that, the frame has nothing
audible to contribute.

The record stored in a reconstruction holds the setup the assignment was made under, one
source per entry naming the recording and the file it was read from, and, per channel, the
stem that holds each frame, parallel to the instruction streams. Every reconstruction carries
one. Together with the instruction streams it is the whole of what a `.stn` says; see
[Reconstructions](../formats/reconstructions.md).

The assignment is greedy per frame, so which stem owns a channel can change from one frame to
the next.
