# Sequencer blocks

A **block** is a rectangle of one sequencer grid, lifted out of the song so it can be written back somewhere else. Copy, cut, paste and delete are the four gestures over it, and both grids, the tracker's pattern rows and the order's frames, carry the same set. Each grid's first column is an **aggregate** that summarizes the channel columns beside it: the tracker's **Voice** column and the order's **Master** row.

This document describes the rules those gestures follow, how a block leaves the app as text, how a selection is drawn, and how a grid's actions reach the menus and the keyboard that fire them. Consult it when changing copy, cut, paste, delete, shifting or selecting in either grid. [Architecture](../architecture.md) describes the layering they sit in, and the [coding guidelines](../guidelines.md) hold the conventions the code follows.

## Three vocabularies, kept apart

A gesture crosses three representations, and each has one owner:

| Term | Where it lives | What it names |
|------|----------------|---------------|
| **Cursor** | `ui/panels/sequencer/input/` | Where the reader is typing, plus the anchor a selection was started from |
| **Region** / **Cell** | `view_model/sequencer/region.py` | The rectangle a gesture acts on, and the single cell a paste is anchored at, in grid coordinates with inclusive bounds |
| **Block** | `logic/sequencer/tracker/`, `logic/sequencer/order/` | The values themselves, keyed by offsets from the cell they were read at |

A region names *where*, and a block carries *what*. A block holds offsets and not coordinates, which lets it land anywhere it is anchored.

Two axes underpin both grids:

- **`CHANNEL_AXIS`** (`constants/sequencer.py`) lists the aggregate first and then the four channels. Index 0 is the aggregate column and 1 to 4 are the channels. Both grids lay out along it, so a row index means the same thing in either.
- **`TrackerSlot`** (`view_model/sequencer/slot.py`) pairs a column with a subcolumn and can be read as a single flat index. Navigation and selection walk the flat index, and an edit addresses the pair.

## A cell reaches a block in one of three states

The block's map alone carries the state, so every consumer reads it the same way:

| State | In the map | Written as |
|-------|-----------|------------|
| A value | Key present, holding it | That value |
| Empty | Key present, holding `None` | Emptiness: the target is cleared |
| Mixed | Key absent | Nothing: the target keeps what it had |

Mixed is what an aggregate cell reads when the channels beneath it disagree, the same `?` the grid displays. Display and clipboard route through one rule, `Agreement` (`sampletones_shared/utils/agreement.py`), so a block says about a cell exactly what the table it was read from shows there.

Absence also settles the order's growth (below): a column a block says nothing about reaches nothing.

## Kind alignment is arithmetic

A tracker block carries subcolumn offsets measured from `column_slot_base(column)`, and every base is a multiple of the subcolumn count. An offset therefore addresses the same kind of subcolumn at whichever column it is replayed against: a voice reference reaches only another voice slot. The paste hook takes a `TrackerCell`, a row and a column with no subcolumn, so the type carries the rule. The anchor decides *where* a block lands, and the block decides *which kind* goes where.

## A paste is a run of the single-cell edits

The writers resolve every cell to the single-cell edit the grid already has. No writer restates the aggregate column's fan-out, so a pasted cell means exactly what the same value typed by hand means. Each write is therefore explainable, and the aggregate's rules have one home.

The order the writes are taken in has two consequences:

- Within a position, the aggregate row is written before the channels beneath it, so a channel cell in the same block overwrites what the aggregate settled. The more specific write wins.
- In the tracker, notes land before the transposes and volumes sharing their row, because placing a sample through the **Voice** column clears the channels of that row.

## The order grows to what a paste reaches

A block pasted past the last frame appends frames. The rule is stated in terms of writes and not of the block's shape: the order grows to the last position a write actually lands at. A `?`-only overrun column appends nothing, and one holding an empty cell appends the frame it silences. Rows clipped at **Noise** take their columns' growth with them.

Growth runs before the first write, so one history entry covers the appended frames and the values in them, and a single undo takes both back. Delete keeps the order's length: emptied trailing frames stay as silent ones.

## A shift reads the columns behind a region

Transpose and volume move whole cells, while a region names its edges as subcolumns. A shift therefore reads the columns a region covers (`TrackerRegion.columns`) and reaches each of their channels once, at every row the region spans. Two consequences follow:

- A nudge raised with the cursor on a volume subcolumn still moves that cell's transpose.
- A region covering the sample column together with a channel beneath it moves that channel a single step, since the sample column stands for the channels a value typed in it writes to.

Each cell reaches the grid through the single-cell adjustment that already governs it, as a pasted cell does. A shift therefore lands exactly the writes the same nudge repeated by hand would make, the transpose and volume ranges included.

## A block states itself as text

A copy also writes the block to the desktop's clipboard, as the lines the grid prints. A tracker block:

```
SampleToNES/1 tracker rows=2 slots=3..5
00 +05 3
.. -02 .
```

and an order block:

```
SampleToNES/1 order rows=1 positions=0..1
00 03
```

The form and its reading live in `logic/sequencer/clipboard/`, which deals in blocks and strings alone. The desktop's clipboard is reached through `TextClipboard` (`utils/gui/clipboard/protocol.py`), one more piece of external behavior behind a protocol ([Architecture](../architecture.md), principle 11). The sequencer coordinator wires the two.

**A field prints what the grid prints in its cell**, which carries the three states across. A value reads as its value, an empty cell as the dots beneath it, and a mixed one as the marks filling its field. The marks fill the whole width, so every line measures the same and a block pasted into a message still reads as a grid. Reading takes any run of them.

**The header is a declaration the body is held to.** It names the grid, the count of rows, and the span of slots or positions the block stands on. A body whose lines or fields disagree with it is not a block. The span also carries the alignment a tracker block needs, since the first slot decides which subcolumn the block opens on.

**A note names its voice by list position**, the figure the grid prints. A block carried to another project therefore plays whichever voice stands at that position there. A position the project's list falls short of reads as mixed, as the writer already treats a voice it has nothing to place.

A field the form has no reading for makes the whole text a refusal, so a parse answers with a block or with nothing. Digits are read in either case, and transpose and volume are held to the ranges a row accepts, so text typed by hand lands the values the grid would.

### Which block a paste writes

A copy writes both clipboards, and a paste asks the desktop for its text first. That text stands while it parses as a block for *that* grid. Any other text leaves the grid's own block in hand. A block copied in a second instance therefore pastes here, and a copy taken in this one survives whatever else the desktop picks up afterward. `can_paste_block` asks the same question through a `ParsedBlockCache`, which reparses only when the text has changed, so opening a menu costs one string compare.

The program that owns the desktop's clipboard answers a read in its own time. A paste therefore writes its block only after the answer arrives. A menu shows Paste based on the last answer it received, and updates the item when the new answer arrives.

## A grid declares its actions once

Where they are shown is decided by whoever asks for them. Each grid builds its whole action set from one **target**: the cell a gesture is aimed at, paired with the region that gesture acts on. Three surfaces resolve that target their own way. The keyboard and the menu bar's **Edit** menu both aim at the cursor's cell and anchor a paste there. A context menu aims at the cell it was raised on and anchors a paste at that cell.

The region behind a target is `region_at` on the shared input state: the selection when the cell falls inside it (`Region.covers`), and the cell alone otherwise. Copying one cell therefore needs no selection made first, and a menu raised inside a selection acts on the whole of it.

One builder means an action added to a grid appears on every surface. The accelerator **Edit** prints is the one that grid answers to, since a binding is declared once and every reader of it reads that entry ([Architecture](../architecture.md), principle 12).

`EditRouter` (`coordinators/edit/`) is the menu-side counterpart of the `KeyRouter` the keyboard runs through. Each surface says whether it owns the editing gestures at this moment, with the same predicate its key scope answers with, so the menu offers what the next press would reach. The router asks the surface that does to build its items into the menu the bar has opened. The router holds no state and resolves the surface on each call, so the menu shows the actions of whoever holds the cursor at the moment it is opened. When no grid answers, the bar shows the clipboard commands grayed out, so a reader working from the menus learns they exist.

**`Del`** carries two meanings, resolved by whether a selection stands. Two ids cannot share a combination inside a shortcut category, so this branch is the route. It also matches tracker convention.

## One gesture, one history entry

Cut, delete and paste each record exactly one entry, whichever surface fired them, and none of them coalesces. A block gesture is already a whole gesture, and folding two consecutive pastes would hide a repeat the reader performed on purpose. Copy runs outside a transaction, since it mutates nothing.

A shift coalesces, because a nudge is a step of one gesture and not a whole one. The block it covers is its coalescing target, so a streak over one selection leaves a single step to undo. A shift after the cursor moves or the selection is reached out starts the next entry. Transpose and volume count separately, each carrying its own action.

## A shape selects to the grid's own edges

`Ctrl+A` and its neighbors select a whole shape at once. The input state gives each shape as a run of bounds along one axis: slots in the tracker, rows in the order. A single builder takes that run, spans the other axis to the grid's full extent, and lands the cursor on the far corner. The whole frame, a column and a subcolumn are therefore three namings of one rectangle, as the whole order and a channel row are of the other. A grid that lays out nothing keeps the selection it had.

The aggregate is an ordinary member of the axis here: selecting the **Voice** column selects a column the way selecting a channel does, and the **Master** row a row.

A press names its shape from the cell the cursor stands on, which is the cell the context menu's items name too, so a key and an item reach the same rectangle. In the tracker a shape ends at the frame's last row, so standing one carries the grid to where the cursor landed, with the same reveal a `Shift+End` reach makes.

## Dragging a range out

Both grids compose one `TableSelection` (`ui/elements/table/selection.py`), which holds what stands painted and the drag gesture that draws it. The grid says which of its cells the selection covers, in its own coordinates. The repaint that follows reaches the cells whose membership changed and marks each through the selectable's own selected state, which the table's theme colors. A rebuilt table asks for a reset, since the cells a selection stood on belong to the body that was replaced.

Both panels read the cell under a held pointer off their own geometry, because DearPyGui reports no hover for the cells a held pointer passes over. A drag carried past an edge reads as the edge, so it selects up to it.

The tracker's row lookup is arithmetic. It measures from the first row's top edge and divides by the row height, which holds while the rows are evenly pitched. That is what the pattern table's zero vertical cell padding and item spacing are for: a vertical padding there would drift the lookup further down the grid. The order's position lookup is arithmetic in the same way and takes its pitch from the first two columns. Its channel lookup walks the rows, because the master row stands apart from the channels beneath it.

### A drag past the edge carries the view

A pointer held past the cells on screen travels the grid under it, so a selection reaches further than the viewport holds. `grid/scroll/` holds the travel. A grid says which axis it scrolls along and where its cells stand along it, and one class reads the two each frame. The tracker travels vertically and the order horizontally, from that same class.

These rules make the travel feel like one gesture:

- **The pointer report drives it.** A held pointer keeps reporting wherever it is carried to, including past the window, so the travel runs off the same report the drag itself reads.
- **The frame's own duration paces it**, so the same stretch of grid passes under the pointer however fast the frames arrive. The pace depends on how far past the edge the pointer stands. It rises from a floor to a ceiling over a few cells' overshoot: a nudge creeps, and a reach covers the grid.
- **Each step is added to the offset last issued.** A table reports the scroll it was drawn with and not the one just set, so a travel that read it back would re-issue an offset it has already reached. The travel rests as soon as the pointer stands within the band again, at the press that opens the next gesture, and on a rebuild. The travel that follows sets out from the offset the grid is drawn with.

## Accepted limitations

- **A rebuilt table starts without a selection.** Both grids reconstruct their input state on rebuild, so following playback and the rebuild after a growing paste leave the cursor and drop the selection. The rows a region named belong to the body that was replaced.
- **The selection stays put after a paste** and does not become the pasted footprint.
- **A note crosses a project by whichever route it took.** The in-app slot survives a project close, because it must survive `on_project_replaced`, which fires on every undo, and it names its voice by id. A note whose voice the project in place lacks is left out of the write, and the target keeps what it had. The clipboard's text names a list position instead, so the same note pasted through it plays whichever voice stands at that position. Transpose and volume are exact by either route.
- **A drag past the edge and the followed playhead both write the scroll.** With **Follow rows** on during playback, the followed playhead carries the sounding row to the head of the band while a held pointer travels the grid, so the two take turns each frame.
