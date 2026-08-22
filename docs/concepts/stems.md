# Stems reconstruction

This document explains how one reconstruction is assigned across several stems.
Consult it when changing the stems assignment algorithm, its configuration, the
per-stem record a reconstruction carries, or the way the application loads,
names, reveals, and plays the recorded stems. The single-sample pipeline this
builds on is described in [Reconstruction](reconstruction.md), and the stored
record in [Reconstructions](../formats/reconstructions.md).

A stems reconstruction converts several audio stems at once. The stems are
mixed and the mix is matched against the instruction library; within each frame,
the channels are handed to the stems one pick at a time, following a precedence
hierarchy. The result is one reconstruction whose `stems_data` records, per
channel and frame, which stem's stream plays.

## Principles

### 1. Every conversion is a stems conversion

Below the conversion job there is one pipeline and one entry point. A job names
the recordings it mixes, the stems setup that hands their channels out, and the
file it writes; a conversion from a single file is the job whose setup holds one
stem over every enabled channel. What the reader chose stays above that line:
the application decides how many jobs a request makes and what setup each
carries, and a batch is many single-source jobs rather than a mode of its own.

This is what lets a channel cap, a hierarchy and a per-source channel set reach
every conversion alike, and what keeps the classic run from being a second path
that has to be kept in step.

### 2. The mix is the target

Every stem is loaded and normalized on its own, padded to the longest stem's
length, and summed. Frames and residuals come from the mix; a stem's own audio
takes no separate part in matching. The working-level coefficient is computed
from the mix, exactly as for a single file.

### 3. One greedy pick at a time

A pick scores each eligible stem's candidates against the current residual with
the same two-stage criterion the single-sample pipeline uses (`FrameMatcher`),
takes the cheapest choice across the active level, subtracts its approximation
from the residual, and consumes the channel. Picks continue until every stem
channel is assigned, or caps and free channels are exhausted. Matching against
the residual is what keeps later picks from re-approximating content earlier
picks already cover.

### 4. A frame is answered whole

Every channel the setup covers leaves a frame either picked or **resting**. A
resting channel holds its channel's null instruction over a silent frame and
records the resting stem id, so instruction streams, rendered approximations and
the per-frame stem record all run parallel to the frames they describe: frame
*i* of a channel is frame *i* of the recording. A channel that rests through
every frame stands by instead, carrying no stream at all.

This is what makes a channel cap and a hierarchy usable. Without it, a frame a
cap left unclaimed would shorten that channel's streams and carry its later
frames early, so what the channel plays would drift out of step with the
recording it was matched against.

### 5. Ownership and decoding compose

The assignment answers *which stem owns which channel this frame*; the decoder
answers *what that channel plays across frames*. Each pick leaves the channel it
won a column of candidates, as wide as the configured decoder reads, and the
decoder chooses one candidate per frame from those columns — greedily, or along
the lowest-cost path through the whole lattice. A resting frame reaches the
decoder as a column of one, so a channel a cap left free sits in the path as the
off state it is. See [Reconstruction §5](reconstruction.md) for the decoders
themselves.

### 6. Precedence orders, mode alternates

The hierarchy groups stem ids into levels that pick in the listed order. In
`strict` mode a level exhausts its stems' channel caps before the next level
picks; in `round_robin` mode the levels take turns, granting every level's stems
one channel per round. Both modes let every stem hold at most `channel_cap`
channels per frame.

### 7. Ties resolve deterministically

Equal-cost choices go to the stem earlier in level order. Channels of one kind
resolve to the lowest free channel, so successive picks over one kind land on
the lowest free channel and a rerun assigns the same way every time.

### 8. The single-sample case stays exact

One stem covering every enabled channel, with a cap at the channel count,
reproduces the classic greedy reconstruction pick for pick. Property tests hold
the assignment against an independent restatement of that reconstruction —
identical choices, instructions, and approximations — so the one pipeline serves
the single-sample case exactly as it stands.

### 9. The working level follows the frame budget

A frame reaches as loud as the channels that may sound in it, so the level the
mix is scaled to is measured against the mixer weights of the loudest covered
channels, as many of them as one frame holds:

```
budget = min(covered channels, stems x channel cap)
```

A capped run therefore targets a level its channels can actually render, and a
setup whose budget covers every channel measures against the same total the
single-sample pipeline always did.

## Mechanics

A request becomes jobs through `reconstructions.converter`: a `ConversionPlan`
answers with the `ConversionJob`s it divides into, resolved against the
configuration the run uses. `GroupConversion` mixes the recordings it is given
into one job, and `DirectoryConversion` scans a folder into one single-source job
per audio file. `ReconstructionConverter` runs those jobs across its worker pool
and reports the reconstructions written.

`StemsConfig` (`reconstructor/stems/configs/`) is the setup: the entries with
their ids and channels, the precedence hierarchy and its mode, and the channel
cap. It validates its own consistency — unique ids, a hierarchy naming every
entry exactly once, a cap of at least one — so an inconsistent setup can be
neither built nor stored, and it derives the views the run reads (`entries_by_id`,
`covered_channels`, `frame_budget`).

The assignment lives in `reconstructor/stems/assignment/`:

- `assign_frame` validates the setup against the run's channels and answers one
  frame whole: the picks in the order they were made, each with its candidate
  column, together with the channels left resting;
- `AssignmentSession` carries one frame's progress — the residual, the free
  channels, the per-stem counts — and runs the hierarchy's mode;
- `TrackAssignment` gathers the frames into what the rest of the run reads: the
  lattice each channel offers the decoder, and the stem owning each of its
  frames.

`Reconstructor.reconstruct` loads the sources, mixes them, assigns every frame,
releases the channels that rested throughout, decodes the remaining lattices,
and folds the decoded streams into the state in frame order — the order each
generator's oscillator phase is carried in.

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

Opening the document loads each recorded stem the way a single source loads
(resampled, normalized and quantized as the configuration asks) and mixes them
with `mix` — padded to the longest stem and summed. The mix is the
original audio the source toggle and the waveform offer, computed fresh on every
load. A recorded stem absent or unreadable on this machine follows the
single-source rule: the whole original is unavailable, the approximation stands
on its own, and the application names the first missing path in its dialog.

The document's name follows the naming rules in
`sampletones_core.reconstructions.naming`, applied to the recorded paths in
order: a single source names the document after the file's stem, several stems
sharing one directory name it after that directory, and paths sharing no
directory fall back to the `.stn` filename.

The reconstruction tab names every recorded path on the Stems card, one row per
stem, each row carrying its own full-path tooltip and revealing its recording on
a click. The Audio source panel keeps the reconstruction's own file and the
choice between the two waveforms. Locating reveals every recorded path according
to the capability matrix in
[Desktop capabilities](../development/desktop-capabilities.md): one file-manager
window with every stem selected where the file manager supports it, one window
per directory otherwise.

## The stems card

The reconstruction tab's Stems card turns the recorded assignment into a
listener the user can steer. It draws the same list the converter's card draws:
each row carries one stem under the level it was picked on, named by its
recording, with a leading master box and a coloured box on every channel the
stem holds frames on. A setup line above the rows names the assignment's
hierarchy mode and channel cap, and a **Collapse levels** toggle draws every row
in one table where the banding is in the way. Ticking a box admits that stem's
frames on that channel to everything the tab plays and exports; unticking
silences them.

### Principles

1. **Selection filters what plays.** A ticked set projects the document rather
   than mutating it: the waveform shows the ticked frames alone, the
   reconstruction toggle plays them mixed, original playback plays the
   recordings heard anywhere mixed, and WAV export writes the same filtered
   projection. Each answer derives from the recorded per-channel assignment, so
   a stem heard on one channel keeps its samples there and stays quiet on the
   next.
2. **A box stands where the choice reaches something.** A stem draws a box on a
   channel exactly where the picker gave it a frame there, so every box the card
   offers changes what is heard. A stem the picker never chose offers none, and
   its row reads as holding no frames.
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
   [Playback](../development/playback.md). Saving the reconstruction records
   the assignment, never the selection. So is the banding: collapsing the levels
   changes how the card draws, never what it describes.
7. **Removing a recording edits the document.** Where a box steers listening,
   the remove button rewrites what is described: the entry leaves the recorded
   setup, its frames rest, and the change is asked about first and recorded in
   the project history. A reconstruction holds at least one recording, so the
   last row standing keeps its button held back.

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
a fresh reconstruction: the entry leaves the setup, taking its level along once
that level holds nothing else; its source path leaves `audio_filepath` from the
position it stood at; every frame it held states the silent instruction, zeroes
its samples and takes `RESTING_STEM_ID`; a channel the removal empties stands
by; and the mixed approximation is summed afresh. The tab coordinator hands the
result on as a `ReconstructionEdit`, the payload both a regenerated instrument
and a removed recording travel as, so one path rebinds the open document and
records the edit against the project history.
