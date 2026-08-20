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
channel and frame, which stem's stream plays — the record multisample playback
will read in the future.

## Principles

### 1. The mix is the target

Every stem is loaded and normalized on its own, padded to the longest stem's
length, and summed. Frames and residuals come from the mix; a stem's own audio
takes no separate part in matching. The working-level coefficient is computed
from the mix, exactly as for a single file.

### 2. One greedy pick at a time

A pick scores each eligible stem's candidates against the current residual with
the same two-stage criterion the single-sample pipeline uses (`FrameMatcher`),
takes the cheapest choice across the active level, subtracts its approximation
from the residual, and consumes the channel. Picks continue until every stem
channel is assigned, or caps and free channels are exhausted. Matching against
the residual is what keeps later picks from re-approximating content earlier
picks already cover.

### 3. Precedence orders, mode alternates

The hierarchy groups stem ids into levels that pick in the listed order. In
`strict` mode a level exhausts its stems' channel caps before the next level
picks; in `round_robin` mode the levels take turns, granting every level's stems
one channel per round. Both modes let every stem hold at most `channel_cap`
channels per frame.

### 4. Ties resolve deterministically

Equal-cost choices go to the stem earlier in level order. Channels of one kind
resolve to the lowest free channel, so successive picks over one kind land on
the lowest free channel and a rerun assigns the same way every time.

### 5. The single-sample case stays exact

One stem covering every enabled channel, with a cap at the channel count,
reproduces the greedy baseline pick for pick. Property tests hold the two paths
to identical choices, instructions, and approximations, so the stems assignment
generalizes the existing pipeline without changing it.

## Mechanics

The assignment lives in `sampletones_core.reconstructions.reconstructor.stems`:

- `Stem` names a competing source and the channels it may occupy;
- `StemHierarchy` carries the precedence levels and the mode;
- `assign_frame` runs one frame's picks against a residual, using the shared
  `FrameMatcher` and `FeatureExtractor` of the pipeline;
- `Reconstructor.reconstruct_stems` loads the stems, mixes them, runs
  `assign_frame` per frame, and records the outcome.

The record stored in a reconstruction (`stems_data`) holds the stems setup the
assignment was made under — the entries, the precedence hierarchy, and the
channel cap — and, per channel, the stem id holding each frame, parallel to the
instruction streams. The record is an optional field, so files written before it
existed load without one.

The stems setup is built per process from the inputs and the user's choices, and
handed to `Reconstructor.reconstruct_stems` together with the stem paths; it is
part of the process rather than of the standard configuration. Per-frame
assignment is greedy for now; Viterbi continuity and playback that decides per
frame on the recorded streams are future work.

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

The reconstruction tab's Audio source panel shows one shortened path line per
stem, each line carrying its own full-path tooltip. Locating reveals every
recorded path according to the capability matrix in
[Desktop capabilities](../development/desktop-capabilities.md): one file-manager
window with every stem selected where the file manager supports it, one window
per directory otherwise.

## The stems card

The reconstruction tab's Stems card turns the recorded assignment into a
listener the user can steer. Each row carries one stem: a checkbox, the recorded
file name, and the channels the stem holds, in entry order. A setup line above
the rows names the assignment's hierarchy mode and channel cap. Checking a stem
admits its frames to everything the tab plays and exports; unchecking silences
them.

### Principles

1. **Selection filters what plays.** A checked set projects the document rather
   than mutating it: the waveform shows the checked stems' frames alone, the
   reconstruction toggle plays their frames mixed, original playback plays
   their recordings mixed, and WAV export writes the same filtered projection.
   Each answer derives from the recorded per-channel assignment, so a stem that
   holds a frame owns its samples everywhere at once.
2. **Every stem starts checked.** A freshly opened stems reconstruction selects
   every recorded stem, which answers the full waveform and the full original —
   the unfiltered document.
3. **The selection follows the open document.** The card lives with the
   reconstruction it describes: opening a document seeds the rows and the
   checked set, a regenerated reconstruction keeps the checked stems and admits
   the newly recorded ones, and closing the document empties the card.
4. **Listening choices stay out of the document.** The checked set is session
   state, like every choice that shapes what is heard — see
   [Playback](../development/playback.md). Saving the reconstruction records
   the assignment, never the selection.

### Mechanics

`ReconstructionData.partials_for` and `ReconstructionData.waveform_data` take
the checked ids and zero the unselected stems' frames per channel before
mixing — `filter_approximations` in
`sampletones_core.reconstructions.reconstruction.stems` — keeping every array
at its unfiltered length, so a filtered mix aligns with the unfiltered one
sample for sample. `ReconstructionPanelLogic` holds the checked set and
re-answers the stems view model, the waveform, and the audio data whenever it
changes; the coordinator wires the card's `on_stems_changed` hook to that
handler. A reconstruction that records one source presents a single implicit
stem for its recording, and one that records no source shows the card's empty
state.
