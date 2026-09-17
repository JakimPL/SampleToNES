# Stems reconstruction

This document explains how one reconstruction is assigned across several stems.
Consult it when changing the stems assignment algorithm, its configuration, the
per-stem record a reconstruction carries, or the way the application loads,
names, reveals, and plays the recorded stems. The single-sample pipeline this
builds on is described in [Reconstruction](reconstruction.md), and the stored
record in [Reconstructions](../formats/reconstructions.md).

A stems reconstruction converts several audio stems at once. Each stem is matched
against the instruction library on its own; within each frame, the channels are
handed to the stems one pick at a time, following a precedence hierarchy. The
result is one reconstruction whose `stems_data` records, per channel and frame,
which stem's stream plays.

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

### 3. A stem sounds at the drive its settings give each channel

A stem's settings name a drive per channel it holds: the factor the channel's
output is scaled by, `1.00` standing at the level the library is calibrated to.
The drive reaches the matching as well as the rendering — candidates are scored
at it and the winning instruction is recorded at it — so a channel pushed harder
is answered by the instructions that carry the recording at that level, and the
frame that reaches the mix sounds at the level it was chosen for. A drive answers
for one channel of one stem, so raising it lifts that part of the mix while the
other stems and the stem's other channels stand where they are.

### 4. A stem sounds where its recording sounds

A stem takes a channel in the frames its own recording reaches a level a channel
can render, and stands aside in the rest. A channel a passing stem leaves free goes
to a stem that does sound there, or rests. This is what keeps a recording quiet
through a passage from sounding that passage on the channels it holds elsewhere.

### 5. One pick at a time, while a pick helps

A pick scores each eligible stem's candidates by the cost of that stem's own frame
with the candidate sounding beside the stem's earlier picks, with the same two-stage
criterion the single-sample pipeline uses (`FrameMatcher`), takes the winning offer
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

A request becomes jobs through `reconstructions.converter`: a `ConversionPlan`
answers with the `ConversionJob`s it divides into, resolved against the
configuration the run uses. `GroupConversion` mixes the recordings it is given
into one job; `BatchConversion` gives each gathered recording a job of its own,
carrying the setup that recording's own row holds and the folder whose tree its
reconstruction mirrors; and `DirectoryConversion` scans a folder into one
single-source job per audio file, which is what the command line converts a
directory as. `ReconstructionConverter` runs those jobs across its worker pool
and reports the reconstructions written.

`StemsConfig` (`reconstructor/stems/configs/`) is the setup: the entries and the
precedence hierarchy with its mode. An entry is an id and the `StemSettings` its
recording is converted with — the channels it may occupy, which of those it
carries toward the divider it really sounds, the drive on each channel it holds,
and how many of them it may sound at once. Every per-recording choice being a
field on those settings is what lets the list a reader sets a run up in, the
entry the run records, and a later reader of that record all state the same
thing. `StemSettings` validates itself — a drive for exactly the channels held,
each within its bounds, and a count of at least one — and `StemsConfig` holds the
ids unique and the hierarchy naming every entry exactly once, so an inconsistent
setup can be neither built nor stored; it derives the views the run reads
(`entries_by_id`, `covered_channels`). `StemSettings.covering(channels)` is the
usual settings over a channel set: those channels, the tone channels among them
bending, unit drive on each, and all of them sounding at once.

The assignment lives in `reconstructor/stems/assignment/`:

- `assign_frame` takes this frame of every stem, keyed by stem id, validates the
  setup against the run's channels, and answers the frame whole: the picks in the
  order they were made, each with its candidate column, together with the channels
  left resting;
- `AssignmentSession` carries one frame's progress — each stem's `FrameMix` and frame
  cost, the free channels, the per-stem counts, and the stems sounding in the frame —
  and runs the hierarchy's mode, then settles the declined channels and scores every
  choice once more. It ranks a level's offers by `StemOffer.improvement`, which the
  matcher measures through `score_column`, `mix_cost` and `reference_energy`;
- `TrackAssignment` gathers the frames into what the rest of the run reads: the
  lattice each channel offers the decoder, and the stem owning each of its
  frames.

`column_groups` (`assignment/columns.py`) gathers the channels a stem still has
free into one group per generator class and drive, the lowest free channel of a
group standing for it. A stem driving its two pulses alike therefore scores them
as one column, as a run without drives does, and a stem driving them apart scores
each. `AssignmentSession` reads a stem's count and its drive per channel from
that stem's own entry, and caches a scored column under the stem, the generator
class and the drive it was scored at.

The drive enters the run where the level matters. `CandidateProvider` serves the
library's powers, waveforms and moments as they stand, and `FrameMatcher` scales
them by the drive a column is scored at — powers and variances by its square,
waveforms and means by the drive itself — so a run at unit drive costs what a run
without drives costs. `Reconstructor._record_streams` then renders each frame at
the drive the stem owning that channel gives it, and a resting frame renders at
unit drive, being silent. Scoring and rendering therefore stand at one level: the
instruction a frame records is the one chosen for the sound that frame makes.

`Reconstructor.reconstruct` loads the sources through `load_stems`, which brings
them to one length and one scale, measures the working level on their mix, frames
each of them, assigns every frame, releases the channels that rested throughout,
decodes the remaining lattices, and folds the decoded streams into the state in
frame order — the order each generator's oscillator phase is carried in.

`STEM_ACTIVITY_FLOOR` is the level a stem's frame reaches to take a channel: the
quietest note any channel renders, measured against the working level.

The record stored in a reconstruction (`stems_data`) holds the stems setup the
assignment was made under and, per channel, the stem id holding each frame,
parallel to the instruction streams. Every reconstruction carries one.

The stems setup is built per conversion from the sources and the reader's
choices and travels with the job; it is part of the request rather than of the
standard configuration. A source the reader left holding no channel takes no part:
the recordings and the entries are derived in one pass, so such a source reaches
neither, and the target stays what the covered channels can render. The assignment
is greedy per frame: continuity of *who* owns a channel across frames, and playback
that decides per frame on the recorded streams, are future work.

## The recorded stems in the application

A stems reconstruction records its stem paths under `audio_filepath` as a tuple,
in entry order; the serialized form carries them in order. The application reads
them through `source_paths`: empty once the reconstruction is detached from its
origin, one path for a single source, the tuple for stems.

Opening the document loads the recorded stems through `load_stems`, the same call
the conversion loads them with, so each one carries the level it holds in the mix
and a stem heard on its own sounds at that level. The mix of them is the original
audio the source toggle and the waveform offer, computed fresh on every load. A
recorded stem absent or unreadable on this machine follows the single-source rule:
the whole original is unavailable, the approximation stands on its own, and the
application names the first missing path in its dialog.

The document's name follows the naming rules in
`sampletones_core.reconstructions.naming`, applied to the recorded paths in
order: a single source names the document after the file's stem, several stems
sharing one directory name it after that directory, and paths sharing no
directory fall back to the `.stn` filename.

The reconstruction tab names every recorded path on the Stems card, one row per
stem, each row carrying its own full-path tooltip and revealing its recording on
a click. The Audio source panel keeps the reconstruction's own file and the
choice between the two waveforms. Locating reveals every recorded path at once:
a Linux file manager offering `org.freedesktop.FileManager1` opens one window
with every stem selected, and every other environment opens one window per
directory holding them.

## The stems card

The reconstruction tab's Stems card turns the recorded assignment into a
listener the user can steer. It draws the same list the converter's card draws:
each row carries one stem under the level it was picked on, named by its
recording, with a leading master box and a colored box on every channel the
stem holds frames on. A setup line above the rows names the assignment's
hierarchy mode, and a **Collapse levels** toggle draws every row
in one table where the banding is in the way. Ticking a box admits that stem's
frames on that channel to everything the tab plays and exports; unticking
silences them.

### Principles

1. **Selection filters what plays, and scopes what is edited.** A ticked set
   projects the document rather than mutating it: the waveform shows the ticked
   frames alone, the reconstruction toggle plays them mixed, original playback
   plays the recordings heard anywhere mixed, and WAV export writes the same
   filtered projection. Each answer derives from the recorded per-channel
   assignment, so a stem heard on one channel keeps its samples there and stays
   quiet on the next. The same set says which frames an instrument edit writes —
   see [Editing a stems reconstruction](#editing-a-stems-reconstruction).
2. **A box stands where the choice reaches something.** A stem draws a box on a
   channel exactly where the record gives it a frame there, so every box the card
   offers changes what is heard. A stem the picker never chose offers none, and
   its row reads as holding no frames. The frames a reader wrote by hand answer
   to no recording, so they gather in a row of their own that reads and behaves
   like any other.
3. **Every stem starts heard everywhere it holds frames.** A freshly opened
   stems reconstruction ticks every box, which answers the full waveform and the
   full original — the unfiltered document.
4. **The global channel choice takes precedence.** A channel switched off for
   the whole reconstruction mutes its column while leaving every value where the
   reader put it, so switching the channel back on restores the per-stem choice
   intact. The two compose by construction: the global choice filters the
   partials, the stems choice the approximations.
5. **The selection follows the open document.** The card lives with the
   reconstruction it describes: opening a document seeds the rows and the ticked
   boxes, a regenerated reconstruction keeps what the reader chose and ticks the
   channels a stem newly reaches, and closing the document empties the card.
6. **Listening choices stay out of the document.** The ticked set is session
   state, like every choice that shapes what is heard — see
   [Playback](../development/application/playback.md). Saving the reconstruction records
   the assignment, never the selection. So is the banding: collapsing the levels
   changes how the card draws, never what it describes.
7. **Removing a recording edits the document.** Where a box steers listening,
   the remove button rewrites what is described: the change is asked about first
   and recorded in the project history, and what it releases is stated under
   [Editing a stems reconstruction](#editing-a-stems-reconstruction). A
   reconstruction holds at least one recording, so the last row standing keeps
   its button held back.

### Mechanics

`ReconstructionData.partials_for` and `ReconstructionData.waveform_data` take a
`StemSelection` — the stems each channel keeps — and zero the unselected frames
per channel before mixing (`filter_approximations` in
`sampletones_core.reconstructions.reconstruction.stems`), keeping every array at
its unfiltered length, so a filtered mix aligns with the unfiltered one sample
for sample. `original_mix_for` mixes the recordings of the stems heard on any
channel. `ReconstructionPanelLogic` holds the channels each stem is heard on and
re-answers the stems view model, the waveform, and the audio data whenever the
choice changes; the coordinator wires the card's `on_stem_channels_changed` hook
to that handler. A reconstruction that records one source presents a single row
for its recording, and one that records no source shows the card's empty
state.

Removal runs through `without_stem`
(`sampletones_core.reconstructions.reconstruction.stems.removal`), which returns
a fresh reconstruction holding what the rule under
[Editing a stems reconstruction](#editing-a-stems-reconstruction) leaves. The tab
coordinator hands the result on as a `ReconstructionEdit`, the payload both a
regenerated instrument and a removed recording travel as, so one path rebinds the
open document and records the edit against the project history.

## Editing a stems reconstruction

A conversion answers, per channel and frame, which recording plays there. Everything a reader
does to the document afterward stands on that answer: the instruments panel rewrites what a
channel plays, the stems card chooses what is heard, and the remove button takes a recording
out. This section states the account of ownership all three keep, and the rules each gesture
follows. Consult it when changing an edit path, the per-frame record, or what the card offers.

### Principles

1. **A frame has exactly one owner.** Every frame of a channel in play is held by one
   recording, by the reader's own hand, or by nobody. The hardware reads one instruction per
   channel per frame, so this is what the channel allows rather than a convention the code
   adopts, and it is what makes the per-frame record a partition of the channel's frames. The
   resting stem id names the frames nobody holds; the **authored** stem id names the frames the
   reader wrote.

2. **Rest and silence name the same frames.** A frame rests exactly when its instruction is
   silent, which the conversion establishes and every later gesture keeps. A reader looking at
   a silent frame and a reader looking at the record therefore learn the same thing, and the
   rules below follow from it rather than choosing around it.

3. **An edit rewrites what a frame plays, and leaves who plays it.** Ownership answers a
   question an edit asks nothing about, so a frame carries its owner through any change to its
   instruction. A frame takes an owner by coming into play and releases it by falling silent.
   This is what lets a reader shape a recording's part while the document keeps its account of
   where that part came from.

4. **What is heard is what is edited.** The channels a recording is ticked on are one choice
   serving two readings: the frames the waveform draws, and the frames an edit writes. A
   recording switched off on a channel reads there and stays as it stands, so a reader reaches
   one recording's part at a time through the card already in front of them.

5. **The setup is the conversion's, and a removal alone rewrites it.** The entries, the levels,
   the channels each recording may occupy, its bends, its drives and its count record how the
   document was made. An edit leaves all of them as they stand. Taking a recording out is the
   one gesture that changes them.

6. **Detaching drops where a recording lives and keeps who played what.** A recording's name and
   the frames it holds belong to the document; its location on this machine belongs to this
   machine. A reconstruction embedded in a project therefore keeps a working stems card.

### What the record holds

The per-frame record answers for every channel in play, and these hold after every gesture:

- a channel in play carries one owner per frame of its stream, each naming a recorded entry,
  the resting stem id or the authored stem id;
- a channel standing by carries no stream and no record at all;
- a frame rests exactly where its instruction is silent;
- a frame a recording holds lies on a channel that recording's settings occupy, while an
  authored frame answers to no settings;
- an entry holding no frame anywhere stays on the record, and its row reads as holding none.

### What an edit carries

An edit hands one channel a fresh set of envelopes, which become that channel's stream. Each
frame's owner follows from the frame it was and the frame it becomes:

| the frame | becomes |
|---|---|
| sounding before and after | its owner, unchanged |
| sounding, edited silent | resting |
| resting, edited into play | authored |
| held by a recording the reader hears, edited into play | its owner, unchanged |
| written past the end of the stream | authored where it sounds, resting where it stays silent |
| dropped from the end of the stream | gone, together with its ownership |

A stream edited down to no frame leaves its channel standing by, and one written back into play
comes back wholly authored. The setup, the recorded sources, the identifier, the configuration
and the working level stand throughout.

**The scope an edit writes in** follows principle 4: a frame accepts a gesture where its owner
is ticked on that channel, where it rests, and where it is authored. Every other frame draws
dimmed and reads as it stands. The scope is the same selection the waveform filter reads, so
one state answers both, and a reader narrowing what they hear narrows what they change with it.

### What a removal releases

Taking a recording out (`without_stem`) releases the frames it held: each states its channel's
silent instruction and takes the resting stem id, and a channel the removal empties stands by.
The entry and its source leave the record, a level the removal empties collapses, and the ids
of the recordings that stay are left alone, so the record and a reader's selection both stay
valid. A reconstruction holds at least one recording, so the last one standing keeps its place.

An edit made before the removal changes nothing about it: the channel carries its record
whatever was written into it, so the frames the recording held are released the way they would
have been. The frames the reader authored answer to no recording and stand through every
removal.
