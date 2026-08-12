# Sequencer blocks

A **block** is a rectangle of one sequencer grid, lifted out of the song so it can be
written back somewhere else. Copy, cut, paste and delete are the four gestures over it,
and both grids — the tracker's pattern rows and the order's frames — carry the same set.

This document states the rules those gestures follow, and how a grid's actions reach the
menus and the keyboard that fire them. The layering they sit in is
[Architecture](architecture.md); the conventions the code is held to are the
[coding guidelines](guidelines.md).

## Three vocabularies, kept apart

A gesture crosses three representations, and each has one owner:

| Term | Where it lives | What it names |
|------|----------------|---------------|
| **Cursor** | `ui/panels/sequencer/input/` | Where the reader is typing, plus the anchor a selection was started from |
| **Region** / **Cell** | `view_model/sequencer/region.py` | The rectangle a gesture acts on, and the single cell a paste is anchored at — grid coordinates, inclusive bounds |
| **Block** | `logic/sequencer/tracker/`, `logic/sequencer/order/` | The values themselves, keyed by offsets from the cell they were read at |

A region names *where*; a block carries *what*. A block holds offsets rather than
coordinates, which is what lets it land anywhere it is anchored.

Two axes underpin both grids:

- **`constants/sequencer.py::CHANNEL_AXIS`** — `(None,) + GeneratorName.items()`. Index 0
  is the aggregate column (the tracker's **Sample**, the order's **Master**) and 1 to 4
  are the channels. Both grids lay out along it, so a row index means the same thing in
  either.
- **`view_model/sequencer/slot.py::TrackerSlot`** — a column paired with a subcolumn,
  readable as a single flat index. Navigation and selection walk the flat index; an edit
  addresses the pair.

## A cell reaches a block in one of three states

The state is carried by the block's map alone, so every consumer reads it the same way:

| State | In the map | Written as |
|-------|-----------|------------|
| A value | Key present, holding it | That value |
| Empty | Key present, holding `None` | Emptiness — the target is cleared |
| Mixed | Key absent | Nothing — the target keeps what it had |

Mixed is what an aggregate cell reads when the channels beneath it disagree, the same
`?` the grid displays. Display and clipboard route through one rule,
`sampletones_shared/utils/agreement.py::Agreement`, so a block states about a cell
exactly what the table it was read from shows there.

Absence is also what settles the order's growth (below): a column a block says nothing
about reaches nothing.

## Kind alignment is arithmetic

A tracker block carries subcolumn offsets measured from `column_slot_base(column)`, and
every base is a multiple of the subcolumn count. An offset therefore addresses the same
kind of subcolumn at whichever column it is replayed against: an instrument value cannot
reach a volume slot. The paste hook takes a `TrackerCell` — a row and a column, with no
subcolumn — so the type states the rule: the anchor decides *where* a block lands and the
block decides *which kind* goes where.

## A paste is a run of the single-cell edits

The writers resolve every cell to a method the grid already has:
`SequencerTrackerLogic.place_note` / `cut_note` / `set_cell_subcolumn` /
`clear_cell_subcolumn`, and `SequencerOrderLogic.write_entry`. Nothing about the aggregate
column's fan-out is restated in a writer, so a pasted cell means exactly what the same
value typed by hand means. That is why each write is explainable, and why the aggregate's
rules have one home.

Two consequences follow from the order the writes are taken in:

- Within a position, the aggregate row is written before the channels beneath it, so a
  channel cell in the same block overwrites what the aggregate settled. The more specific
  write wins.
- In the tracker, notes land before the transposes and volumes sharing their row, because
  placing a sample through the **Sample** column clears the channels of that row.

## The order grows to what a paste reaches

A block pasted past the last frame appends frames, and the rule is stated in terms of
writes rather than the block's shape: the order grows to the last position a write
actually lands at. A `?`-only overrun column appends nothing; one holding an empty cell
appends the frame it silences. Rows clipped at **Noise** take their columns' growth with
them.

Growth runs before the first write, so one history entry covers the appended frames and
the values in them, and a single undo takes both back. Delete keeps the order's length:
emptied trailing frames stand as silent ones.

## A shift reads the columns behind a region

Transpose and volume move whole cells, while a region names its edges as subcolumns. A shift
therefore reads the columns a region covers (`TrackerRegion.columns`) and reaches each of their
channels once, at every row the region spans. Two consequences follow: a nudge raised with the
cursor on a volume subcolumn still moves that cell's transpose, and a region covering the sample
column together with a channel beneath it moves that channel a single step, since the sample column
stands for the channels a value typed in it writes to.

Each cell reaches the grid through the single-cell adjustment that already governs it, the way a
pasted cell does, so a shift lands exactly the writes the same nudge repeated by hand would make —
the transpose and volume ranges included.

## A grid declares its actions once

Where they are shown is decided by whoever asks for them. Each grid builds its whole
action set from one **target** — the cell a gesture is aimed at, paired with the region
that gesture acts on — and three doors resolve that target their own way:

| Door | Aims at | Anchors a paste at |
|------|---------|--------------------|
| The keyboard | the cursor's cell | the cursor |
| A context menu | the cell it was raised on | the clicked cell |
| The menu bar's **Edit** menu | the cursor's cell | the cursor |

The region behind a target is `region_at` on the shared input state: the selection when the
cell falls inside it (`Region.covers`), and the cell alone otherwise. So copying one cell
needs no selection made first, and a menu raised inside a selection acts on the whole of it.

One builder means an action added to a grid appears at every door, and the accelerator
**Edit** prints is the one that grid answers to, since a binding is declared once and every
reader of it reads that entry ([Architecture](architecture.md), principle 12).

`EditRouter` (`coordinators/edit/`) is the menu-side counterpart of the `KeyRouter` the
keyboard runs through. Each surface states whether it owns the editing gestures at this
moment — the same predicate its key scope answers with, so the menu offers what the next
press would reach — and the router asks the one that does to build its items into the menu
the bar has opened. It holds no state, resolving the surface on each call, so the menu
states the actions of whoever holds the cursor at the moment it is opened. The bar names the
clipboard four greyed out when no grid answers, which is how a reader working from the menus
learns the commands exist.

**`Del`** carries two meanings, resolved by whether a selection stands. Two ids cannot share
a combination inside a shortcut category, so this branch is the route; it also matches
tracker convention.

## One gesture, one history entry

Cut, delete and paste each record exactly one entry, whichever door fired them, and none of
them coalesces: a block gesture is already a whole gesture, and folding two consecutive
pastes would hide a repeat the reader performed on purpose. Copy runs outside a transaction,
since it mutates nothing.

A shift coalesces, because a nudge is a step of one gesture rather than a whole one. The block it
covers is its coalescing target, so a streak over one selection leaves a single step to undo and a
shift after the cursor moves or the selection is reached out starts the next entry. Transpose and
volume count separately, each carrying its own action.

## Dragging a range out

Both grids compose one `TableSelection` (`ui/elements/table/selection.py`), which holds what
stands painted and the drag gesture that draws it. The grid states which of its cells the
selection covers, in its own coordinates; the repaint that follows reaches the cells whose
membership changed, marking each through the selectable's own selected state, which the
table's theme colours. A rebuilt table asks for a reset, since the cells a selection stood on
belong to the body that was replaced.

Both panels read the cell under a held pointer off their own geometry, because DearPyGui
reports no hover for the cells a held pointer passes over. A drag carried past an edge
reads as the edge, so it selects up to it.

The tracker's row lookup is arithmetic: it takes the first row's top edge and divides by
`layout.tracker.row_height`. That holds only while the rows are evenly pitched, which is
what `CellPadding.y = 0` and `ItemSpacing.y = 0` in `theme/tables/pattern.yaml` are for.
A vertical padding there would drift the lookup further down the grid. The order's
position lookup is arithmetic in the same way, taking its pitch from the first two
columns; its channel lookup walks the rows, because the master row stands apart from the
channels beneath it.

## Accepted limitations

- **A rebuilt table has no selection.** Both grids reconstruct their input state on
  rebuild, so following playback and the rebuild after a growing paste leave the cursor
  and drop the selection. The rows a region named belong to the body that was replaced.
- **The selection stays put after a paste** rather than becoming the pasted footprint.
- **Cross-project paste is lossy in the note column and exact in transpose and volume.**
  A slot survives a project close, because it must survive `on_project_replaced`, which
  fires on every undo; a note naming a sample the project in place lacks is left out of
  the write, and the target keeps what it had.
