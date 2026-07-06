# The sequencer

The **Sequencer** tab is a tracker: it arranges reconstructions into a song across
the four NES channels and exports it as a FamiTracker
[module](../formats/famitracker.md) (`.ftm`). It works on a
[project](../formats/projects.md), so start one with **File ▸ New project** (or
open an existing `.stp`). The pattern grid and order sit in the centre, a browser
for pulling in reconstructions on the left, and the module settings, sample list,
and undo history on the right.

## Adding samples

A song is built from **samples** — reconstructions imported as playable
instruments. Add one from the **Reconstructions** browser on the left (right-click
▸ **Add to Sequencer**), or with **Add to Sequencer** on the **Reconstructions**
tab. If a reconstruction was made at a different NES frequency than the project and
the project already has samples, _SampleToNES_ warns with **Different NES
frequency**; **Add anyway** adds it regardless.

Manage the imported samples in the **Samples** list on the right: right-click one
to **Rename**, **Duplicate**, **Remove**, or reorder it, and toggle its **Loop**
flag. Removing a sample that patterns still use asks **Remove sample** first,
because it clears every row that references it.

## Writing a pattern

The **Tracker** grid is the pattern editor. Each row is one step in time; the
columns are the **Sample** and the four channels — **Pulse 1**, **Pulse 2**,
**Triangle**, **Noise** — each carrying a note, volume, and transpose. Click a cell
and type on your keyboard to enter a note, piano-style. Right-clicking a cell opens
the rest of the operations — **Set instrument**, **Note off**, **Clear cell** and
**Clear row**, transpose and volume adjustments, and **Play from here** to audition
from that row. The transport below the grid plays the song, and **Follow playback**
scrolls the grid to keep pace.

## Arranging the song

A song plays a sequence of patterns, and the **Order** grid sets that sequence —
one column per position, with a row for the master and each channel. Type an entry
to place a pattern, or right-click a frame to **Insert frame**, **Duplicate**,
**Clear frame**, **Remove**, move it, or **Play from here**.

## Timing and properties

Set the song's timing in **Module options** on the right: **Rows** per pattern,
**Tempo**, **Speed**, and the **NES frequency**. Changing the **NES frequency**
after samples exist re-times how they all play back, so it asks **Change NES
frequency** first (with a **Don't ask again** option).

The project's title, author, and comment — which carry into the exported module —
are set in **Project properties**, from the button or **File ▸ Project
properties...**.

## Undo and export

Every change is undoable. The **History** panel on the right shows the stack, with
**Undo** and **Redo** (also on the **Edit** menu); click any entry to jump straight
to that point.

When the song is ready, **Export as FamiTracker module** (or **File ▸ Export
FamiTracker module...**) writes the `.ftm`. See
[FamiTracker export](../formats/famitracker.md) for what the module contains and
the limits it respects.
