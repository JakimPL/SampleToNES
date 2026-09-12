# The sequencer

The **Sequencer** tab is a tracker: it arranges voices into a song across the four
NES channels and exports it as a FamiTracker
[module](../formats/famitracker.md) (`.ftm`). It works on a
[project](../formats/projects.md), so start one with **File ▸ New project** (or
open an existing `.stp`). The pattern grid and order sit in the center, a browser
for pulling in reconstructions on the left, and the module settings, voice list,
and undo history on the right.

## Voices: samples and instruments

A song is built from **voices**, and there are two kinds. A **sample** is a
reconstruction brought in as something a row can play. An **instrument** is written by
hand — envelopes with no recording behind them — for the melodies and basses you write
yourself. Both sit in the **Voices** list on the right, numbered together, and a
mark at the front of each row says which kind it is. The mark carries a color as well
as a shape — amber for a sample, magenta for an instrument — and the same two colors
name a voice in the pattern grid and in the history, so the two kinds read apart
wherever one is named.

Four ways bring a voice in, and the **Voice** menu holds all four:

| Way in | What arrives |
|--------|--------------|
| **New instrument** | An instrument holding a note at full volume, ready to place and hear |
| **Add sample from file...** | A reconstruction saved anywhere on disk, as a sample |
| **Import instrument...** | A FamiTracker instrument file (`.fti`), as an instrument |
| **Add to Sequencer** | The reconstruction the **Reconstruction** tab holds, as a sample |

The first three also sit at the top of the **Voices** list, and on the list's own
menu — right-click below the rows to reach it. **Add to Sequencer** is on the
**Browser** on the Sequencer tab (right-click a reconstruction) and on the
**Reconstruction** tab. If a reconstruction was made at a different NES frequency
than the project and the project already has voices, _SampleToNES_ warns with
**Different NES frequency**; **Add anyway** adds it regardless.

A new instrument starts out holding a note at full volume, so you can place it and
hear it straight away; give it the sound you want on the **Reconstruction** tab
(right-click ▸ **Edit**). See [editing instruments](reconstruction.md#editing-instruments).
An imported `.fti` arrives with the volume, arpeggio, and duty-cycle envelopes the
file states, and **Instrument imported** names anything the file held on a tracker's
own terms that the voice leaves behind — see [reading an instrument
file](../formats/famitracker.md#c-reading-an-instrument-file).

**New instrument from ▸ _channel_** on a sample's menu writes what one of its channels
plays into an instrument of its own, so a recorded part becomes envelopes you edit by
hand.

Right-click any voice to **Edit**, **Rename**, **Duplicate**, **Remove**, or reorder it.
**Export instrument...** writes the voice out as a `.fti` another tracker reads — a
sample holds one instrument per channel it plays, so it asks which. The **Edit** menu
carries the same actions for the voice you have picked. The right-click menu also names
how much room the voice takes on the NES — a sample's total and then each channel it
plays, and an instrument's single figure. The figures are in bytes, and they count what a
FamiTracker export saves. Removing a voice that patterns still use asks first, because it
clears every row that references it.

Hovering a row says what that voice is in one line: its name, whether it is a sample or
an instrument, the channels a sample plays, and the room it takes.

## Writing a pattern

The **Tracker** grid is the pattern editor. Each row is one step in time; the
columns are the **Sample** and the four channels — **Pulse 1**, **Pulse 2**,
**Triangle**, **Noise** — each carrying a voice, a pitch, and a volume. Click a cell
and type its value. Right-clicking a cell opens the rest of the operations — **Set
voice**, **Note off**, **Clear cell** and **Clear row**, transpose and volume
adjustments, **Play from here** to audition from the cursor row, and **Play from
this frame** to start at the top of the shown frame.

The **Sample** column places a sample across every channel its reconstruction
covers, and clears the rest of the row. It takes samples alone: an instrument sounds
on the one channel that names it, so **Set voice** lists instruments there grayed out,
and a number typed over one leaves the cell reading what it held. Name an instrument
in the channel column you want it on.

A cell holding a voice wears that voice's color — amber for a sample, magenta for an
instrument — while an empty cell, a cut, and a `?` where the **Sample** column's
channels disagree read in a plain gray. Silencing a channel dims its cells and keeps
those colors, so a muted column stays as readable as the rest.

## Reading and typing a pitch

A pitch cell holds one number, and it reads in the terms of the voice the channel is
carrying. A sample was converted at a pitch of its own, so its cells read as steps
from it — `+00` plays it as recorded, `+0C` an octave up. An instrument sounds at
whatever note a row names it with, so its cells read as the notes they sound — `C-4`,
`A#3`.
A row that only bends a note reads the same way as the row that started it.

Type a note into an instrument's cell piano-style: the bottom two rows of the keyboard are
one octave (`Z` `S` `X` `D` `C` …) and the two above them the next (`Q` `2` `W` `3`
`E` …). **Octave** above the grid says where the bottom row opens. The keys work on
a sample's cell too, writing the step that reaches the note you pressed. The noise
channel selects one of sixteen periods rather than a note, so its cells are typed as
a signed value.

## Arranging the song

A song plays a sequence of patterns, and the **Order** grid sets that sequence —
one column per position, with a row for the master and each channel. Type an entry
to place a pattern, or right-click a frame for the rest: **Duplicate** repeats the
frame with the patterns it already plays, **Clone** gives the copy patterns of its
own so you can change it on its own, and **Insert frame**, **Clear frame**,
**Remove**, the moves, and **Play from this frame** do what they say.

## Working on a block

Both grids take a **selection** — a rectangle of cells you copy, cut, paste, and
delete in one go. Hold `Shift` and press the arrow keys to reach out from the
cursor, or drag the pointer across the cells; `Shift`+click carries the selection to
the cell you click. Dragging past the edge of a grid scrolls it along, so a selection
can run further than the screen shows. Any plain move, and `Escape`, puts the
selection away again.

| Key | Action |
|-----|--------|
| `Shift`+arrows | Reach the selection out a cell at a time |
| `Shift+Home` / `Shift+End` | Reach it to the first or the last row (tracker) or position (order) |
| `Ctrl+A` | Select the whole frame, or the whole order |
| `Ctrl+Shift+A` | Select the column you are in (tracker), or your channel's row (order) |
| `Ctrl+Alt+A` | Select the subcolumn you are in (tracker) |
| `Ctrl+C` | Copy |
| `Ctrl+X` | Cut — copy, then empty what was selected |
| `Ctrl+V` | Paste, starting at the cursor |
| `Del` | Empty the selection |

Copy, cut, paste and delete act on the cell the cursor stands on when nothing is
selected, so copying one cell needs no selection first. All four sit on each grid's
right-click menu: raised inside a selection they act on the whole of it, raised
anywhere else on the cell you clicked. Each grid keeps its own copy, so a tracker
block pastes into the tracker and an order block into the order.

The **Select** keys work from the cell you are on and reach the whole length of the
grid. They sit on the right-click menu too.

A paste is anchored: the block starts at the cell you paste onto and lands the rest
down and to the right of it.

In the **Tracker**, a block keeps the kinds of the cells it came from — a transpose
lands in a transpose, a volume in a volume, whichever column you paste onto — and
whatever reaches past the last row or the last column is left out. A cell reading
`?`, where the **Sample** column's channels disagree, passes over its target and
leaves what was there; an empty cell empties it.

In the **Order**, a block pasted past the last frame grows the song to hold it, and
one reaching past the **Noise** row stops there. The **Master** row copies the index
its channels share and reads `?` when they differ, which pasted leaves each channel
as it was.

Emptying cells keeps the rows and frames they sit in, and every block action is one
step in the history, so a single **Undo** takes it all back.

A copy also goes to your desktop's clipboard as plain text, so a block carries between
two open windows of _SampleToNES_ — copy in one, paste in the other — and you can paste
one into a message to show someone what you wrote. Anything else on the clipboard
leaves you with the last block you copied here. Notes travel by their number in the
**Voices** list, so a block pasted into another project plays whichever voice holds
that number there.

## Transposing and shading

In the **Tracker**, transpose and volume move whatever the selection covers, so a
run of rows nudges together.

| Key | Action |
|-----|--------|
| `Ctrl+Up` / `Ctrl+Down` | Transpose a semitone |
| `Ctrl+Shift+Up` / `Ctrl+Shift+Down` | Transpose an octave |
| `Alt+Up` / `Alt+Down` | Volume a step |
| `Alt+Shift+Up` / `Alt+Shift+Down` | Volume four steps |

Control carries pitch, Alt carries volume, and Shift makes the step the bigger one.
With nothing selected they act on the cell the cursor stands on, and the same
commands sit on the right-click menu with these keys beside them.

## Playing the song

The transport below the grid plays the song, and the keyboard drives playback
throughout the tab:

| Key | Action |
|-----|--------|
| `Space` | Play, or pause and resume what is playing |
| `Shift+Space` | Play from the start |
| `Ctrl+Space` | Play from the frame currently shown |
| `Ctrl+Shift+Space` | Play from the cursor's row in the pattern grid |
| `Escape` | Stop |
| `Ctrl+L` | **Loop song** — start the song over each time it reaches the end |

`Escape` silences everything, including a sample preview. The same commands sit on
the **Playback** menu and the transport buttons.

## Following the playhead

**Playback ▸ Follow playback** chooses how far the view travels with the sounding
row. Each mode carries a key of its own, so you can change your mind while the song
plays, and the choice is remembered for the next time you launch:

| Mode | Key | Where the view goes |
|------|-----|---------------------|
| **Follow rows** | `Ctrl+F` | Scrolls the pattern grid to keep the sounding row on screen, and shows the frame being played |
| **Follow patterns** | `Ctrl+Shift+F` | Shows the frame being played, and leaves the scroll where you put it |
| **Don't follow** | `Ctrl+Alt+F` | Holds the view where you put it |

The **Order** grid marks the frame being played under every mode, and the tracker
marks the sounding row of the frame it shows — so a held view still shows the
playhead each time the song passes through the frame you are editing.
**Follow rows** is the one that moves the grid while you play, which is what makes
the other two the modes to type in: they hold the view still under your cursor while
the song runs.

## Listening to one channel at a time

Channel names are switches. Click **Triangle** at the top of the tracker to silence
that channel: its name grays, its column and its row in the **Order** grid go
neutral, and its notes dim — still readable, still editable, just not sounding.
Click the name again to bring it back. The same click works on the channel's name
in the **Order** grid, and both grids show every change, so a channel looks the same
wherever you see it.

| Gesture | Action |
|---------|--------|
| Click a channel's name | Silence it, or bring it back |
| `Ctrl`+click a channel's name | Solo it — silence the other three; `Ctrl`+click again returns the mix you had |
| Click **Sample** (tracker) or **Master** (order) | Silence every channel, or bring them all back |
| Right-click any name | The same actions as a menu |

The **Playback ▸ Channels** submenu carries the same mix: a check marks each channel
that sounds, and **Unmute all channels** returns the whole set. `1` to `4` do the
same from the keyboard, one key per channel, wherever the grids are not holding your
cursor — inside them the digits enter values.

Muting is for listening only. The song keeps every channel, so saving, exporting a
module, and undo all work on the full arrangement, and a mute survives undo and
redo. Toggling during playback is heard within about a quarter second. Opening,
creating, or closing a project starts a fresh listening session with every channel
audible.

## Timing and properties

Set the song's timing in **Module options** on the right: **Rows** per pattern,
**Tempo**, **Speed**, and the **NES frequency**. Changing the **NES frequency**
after voices exist re-times how they all play back, so it asks **Change NES
frequency** first (with a **Don't ask again** option).

The project's title, author, and comment — which carry into the exported module —
are set in **Project properties**, from the button or **File ▸ Project
properties...**, along with the meter the song is counted in.

**First highlight** and **Second highlight** are that meter: how many rows make a
beat, and how many make a bar. The tracker tints the row that opens each one. The
bar divided by the beat is how many beats you hear in a bar, so the default 4 and
16 give four beats of four rows — common time. Waltz time keeps the four-row beat
and shortens the bar to 12, for three beats. The beat is what the tempo counts, so
the two together say how fast the song is felt as well as how it looks.

The meter also places the song's timing. Most tempos ask for a row length the engine
can only reach on average, so the rows of a bar differ a little: the meter gives the
extra time to the row that opens the bar, then to the row that opens each beat, which
keeps the beat audible where you expect it.

## Undo and export

Every change is undoable. The **History** panel on the right shows the stack, with
**Undo** and **Redo** (also on the **Edit** menu); click any entry to jump straight
to that point.

When the song is ready, **Export as FamiTracker module** (or **File ▸ Export
FamiTracker module...**) writes the `.ftm`. See
[FamiTracker export](../formats/famitracker.md) for what the module contains and
the limits it respects.

**File ▸ Export ▸ NSF program...** writes the song as an `.nsf` instead: a program
the console itself plays, carrying its own player, so it needs no tracker to sound.
The console holds one program in 32 KB, so a long song can outgrow it — the export
says so rather than writing a file that plays part of itself. See
[NSF export](../formats/nsf.md) for what the file holds, and
[song compression](../concepts/compression.md) for how a song of minutes is fitted
into that space.

## Rendering to audio

A module is for a tracker. To get a file anyone can play, use **File ▸ Render
song...** (`Ctrl+Shift+E`), which writes the whole song as audio.

The dialog holds the choices:

| Setting | What it does |
|---------|--------------|
| **Format** | **WAV** for the full-quality file, **MP3** for a smaller one |
| **Sample rate** | How many samples a second the file holds; 44100 Hz is the usual choice |
| **Bit depth** (WAV) | How finely each sample is stored. 16-bit PCM is the usual choice; 8-bit is there for the crunch the NES itself has |
| **Bitrate** (MP3) | How much the file spends per second — higher sounds better and takes more room. What is on offer depends on the sample rate, so the list follows when you change it |
| **Normalize peak** | Lifts the whole song so its loudest moment reaches full scale, keeping the balance between channels as it was |
| **File** | Where it is written. **Browse...** opens the save dialog, clicking the path shows where the file is going in your file manager, and the folder you pick is offered again next time |

**Length** tells you how long the file will be before you start. **Render** begins,
and a bar reports how far it has got; **Cancel** stops it and leaves the file
unwritten. When it finishes, _SampleToNES_ shows the file it wrote — click the path
to open its folder.

A render takes the song itself, once through, with every channel sounding: muting
and **Loop song** are for listening and stay out of the file. It is one of the long
jobs that run alone, so the item is unavailable while a conversion or a library
generation is going, and those wait for a render in the same way.
