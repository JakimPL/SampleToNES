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
**Clear row**, transpose and volume adjustments, **Play from here** to audition from
the cursor row, and **Play from this frame** to start at the top of the shown frame.

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
the cell you click. Any plain move, and `Escape`, puts it away again.

| Key | Action |
|-----|--------|
| `Shift`+arrows | Reach the selection out a cell at a time |
| `Shift+Home` / `Shift+End` | Reach it to the first or the last row (tracker) or position (order) |
| `Ctrl+C` | Copy |
| `Ctrl+X` | Cut — copy, then empty what was selected |
| `Ctrl+V` | Paste, starting at the cursor |
| `Del` | Empty the selection |

With nothing selected these act on the cell the cursor stands on, so copying one
cell needs no selection first. The same four sit on each grid's right-click menu:
raised inside a selection they act on the whole of it, raised anywhere else on the
cell you clicked. Each grid keeps its own copy, so a tracker block pastes into the
tracker and an order block into the order.

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
that channel: its name greys, its column and its row in the **Order** grid go
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
that sounds, and **Unmute all channels** returns the whole set. `F1` to `F4` do the
same from the keyboard, one key per channel.

Muting is for listening only. The song keeps every channel, so saving, exporting a
module, and undo all work on the full arrangement, and a mute survives undo and
redo. Toggling during playback is heard within about a quarter second. Opening,
creating, or closing a project starts a fresh listening session with every channel
audible.

## Timing and properties

Set the song's timing in **Module options** on the right: **Rows** per pattern,
**Tempo**, **Speed**, and the **NES frequency**. Changing the **NES frequency**
after samples exist re-times how they all play back, so it asks **Change NES
frequency** first (with a **Don't ask again** option).

The project's title, author, and comment — which carry into the exported module —
are set in **Project properties**, from the button or **File ▸ Project
properties...**, along with the metre the song is counted in.

**First highlight** and **Second highlight** are that metre: how many rows make a
beat, and how many make a bar. The tracker tints the row that opens each one. The
bar divided by the beat is how many beats you hear in a bar, so the default 4 and
16 give four beats of four rows — common time. Waltz time keeps the four-row beat
and shortens the bar to 12, for three beats. The beat is what the tempo counts, so
the two together say how fast the song is felt as well as how it looks.

The metre also places the song's timing. Most tempos ask for a row length the engine
can only reach on average, so the rows of a bar differ a little: the metre gives the
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
