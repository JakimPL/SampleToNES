# Sequencer blocks

A **block** is a rectangle of one sequencer grid, lifted out of the song so it can be
written back somewhere else. Copy, cut, paste and delete are the four gestures over it,
and both grids — the tracker's pattern rows and the order's frames — carry the same set.

This document states the rules those gestures follow. The layering they sit in is
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

## What a gesture acts on

- **From the keyboard**: the selection, or — with none up — the cursor's own cell.
  `region_at` on the shared input state is where that fallback lives, so copying one cell
  needs no selection made first.
- **From a context menu**: the selection when the menu was raised inside it, and the
  clicked cell otherwise (the same `region_at`, over `Region.covers`). A paste from a menu
  anchors at the clicked cell; a paste from the keyboard anchors at the cursor.
- **`Del`** carries two meanings, resolved by whether a selection stands. Two ids cannot
  share a combination inside a shortcut category, so this branch is the route; it also
  matches tracker convention.

Copy is wired straight through rather than through `_undoable` — it mutates nothing, so a
transaction over it would record an entry with nothing to restore. Cut, delete and paste
each record exactly one entry, and none of them coalesces: a block gesture is already a
whole gesture, and folding two consecutive pastes would hide a repeat the reader performed
on purpose.

## Dragging a range out

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
