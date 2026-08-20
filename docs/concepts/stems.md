# Stems reconstruction

This document explains how one reconstruction is assigned across several stems.
Consult it when changing the stems assignment algorithm, its configuration, or
the per-stem record a reconstruction carries. The single-sample pipeline this
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
