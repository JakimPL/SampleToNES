# The sequencer

The **Sequencer** tab (`F3`) is a [tracker](../glossary.md#tracker--sequencer). You use it to arrange
voices into a song on the four NES [channels](../glossary.md#channel). You can play the song back,
export it, or render it to audio.

The sequencer works on a [project](../formats/projects.md). Choose **File ▸ New project** to start
one, or open an existing `.stp` file.

## Voices: samples and instruments

A song plays [**voices**](../glossary.md#voice). There are two kinds:

- A **sample** is a reconstruction that the song plays.
- An **instrument** is a sound you write by hand. Use instruments for melodies and bass lines.

Both kinds are in the **Voices** list, numbered together.

The **Voice** menu adds a voice in four ways:

| Menu item | What it adds |
|-----------|--------------|
| **New instrument** | An instrument that plays a note at full volume, ready to place and hear |
| **Add sample from file...** | A reconstruction file from anywhere on your disk, as a sample |
| **Import instrument...** | A FamiTracker instrument file (`.fti`), as an instrument |
| **Add to Sequencer** | The reconstruction open on the **Reconstruction** tab, as a sample |

The first three items are also at the top of the **Voices** list. Right-click below the rows of the
list to open the same menu. **Add to Sequencer** is on the **Reconstruction** tab as well, and in the
right-click menu of any reconstruction in the **Browser**.

If a reconstruction uses a different [NES frequency](../glossary.md#nes-frequency) than the project,
the app shows **Different NES frequency**. Click **Add anyway** to add it.

Right-click a voice to rename, duplicate, move or remove it. Some commands do more than their names
say:

- **Edit** opens the voice on the **Reconstruction** tab, where you change how it sounds. See
  [editing instruments](reconstruction.md#editing-instruments).
- **New instrument from**, on a sample, copies what the sample plays on one channel into a new
  instrument you can edit.
- **Export instrument...** saves the voice as an `.fti` file. A sample has one instrument per
  channel, so the app asks which channel to export.

The same commands are on the **Edit** menu for the voice you selected. The right-click menu also
shows how many bytes the voice takes on the NES. This matters when you export an NSF program.

Removing a voice that patterns still use asks you first, and clears every row that uses it.

An imported `.fti` file keeps its volume, arpeggio and duty cycle sequences. **Instrument imported**
lists any other settings the file carried, which the instrument leaves out. See [reading an
instrument file](../formats/famitracker.md#c-reading-an-instrument-file).

## Writing a pattern

The **Tracker** grid is the [pattern](../glossary.md#pattern) editor. Each row is one step in time.
The grid has a **Sample** column and a column for each channel: **Pulse 1**, **Pulse 2**,
**Triangle** and **Noise**. Each channel column has a voice, a pitch and a volume.

Click a cell and type its value. Right-click a cell for the same commands as a menu, including
**Note off**, which stops the note.

The [**Sample** column](../glossary.md#sample-column) places a sample on every channel the sample
uses, and clears the other channels of the row. It takes samples only. To place an instrument, use
the column of the channel you want it on.

A `?` in the **Sample** column means the channels of that row play different voices.

## Typing a pitch

A pitch cell shows a number. What the number means depends on the voice:

- For a sample, the number is a step from the pitch the sample was recorded at. `+00` plays the
  sample as recorded. `+0C` plays it one octave higher.
- For an instrument, the number is a note, such as `C-4` or `A#3`.

Type notes on your keyboard like a piano:

- The bottom two rows of keys play one octave: `Z` `S` `X` `D` `C` and so on.
- The two rows above them play the next octave: `Q` `2` `W` `3` `E` and so on.

**Octave**, above the grid, sets the octave of the bottom row. The same keys work in a sample's cell
and type the step that plays the note you pressed.

The noise channel has sixteen sounds in place of notes. Type a noise cell as a step with a sign, such
as `+03` or `-02`.

## Arranging the song

A song plays patterns in a sequence. The [**Order**](../glossary.md#order) grid sets that sequence.
Each column is one position in the song, called a **frame**. The grid has a row for the **Master**
and a row for each channel.

Type a pattern number in the **Order** grid to place a pattern. Right-click a frame to insert, clear
or remove frames, and to repeat one:

- **Duplicate** repeats the frame with the same patterns, so a change to one shows in both.
- **Clone** repeats the frame with new copies of its patterns, so you can change them separately.

## Playing the song

The play controls under the grid play the song. These keys work anywhere on the tab:

| Key | Action |
|-----|--------|
| `Space` | Play, or pause and resume |
| `Shift+Space` | Play from the start |
| `Ctrl+Space` | Play from the frame on screen |
| `Ctrl+Shift+Space` | Play from the cursor's row |
| `Esc` | Stop |
| `Ctrl+L` | **Loop song**: start the song again when it ends |

`Esc` also stops a sample preview. The same commands are on the **Playback** menu, and each grid's
right-click menu plays from the row or frame you clicked.

## Following the playback

**Playback ▸ Follow playback** chooses whether the view moves with the song. The app remembers your
choice.

| Mode | Key | What the view does |
|------|-----|---------------------|
| **Follow rows** | `Ctrl+F` | Scrolls the tracker to the playing row, and shows the playing frame |
| **Follow patterns** | `Ctrl+Shift+F` | Shows the playing frame, and keeps your scroll position |
| **Don't follow** | `Ctrl+Alt+F` | Stays where you put it |

In every mode, the **Order** grid marks the playing frame, and the tracker marks the playing row.
Use **Follow patterns** or **Don't follow** to type while the song plays.

## Muting channels

Click a channel's name at the top of the tracker to mute the channel. Click the name again to unmute
it. The channel names in the **Order** grid work the same way.

| Gesture | Action |
|---------|--------|
| Click a channel's name | Mute or unmute the channel |
| `Ctrl`+click a channel's name | Solo the channel: silence the rest. `Ctrl`+click again to restore the previous mix |
| Click **Sample** (tracker) or **Master** (order) | Mute or unmute every channel |
| Right-click a name | The same commands as a menu |

**Playback ▸ Channels** shows which channels play. **Unmute all channels** unmutes all four. Keys
`1` to `4` mute and unmute a channel when the cursor is outside the grids. Inside the grids, the
digit keys type values.

Muting changes only what you hear. Saving, exporting, rendering and undo use every channel. Opening,
creating or closing a project unmutes all channels.

## Selecting, copying and pasting

You can select a block of cells in both grids, then copy, cut, paste or delete it.

To select cells:

- Hold `Shift` and press the arrow keys.
- Drag across the cells with the mouse.
- `Shift`+click a cell to extend the selection to it.

Dragging past the edge of a grid scrolls the grid. Any plain arrow key, or `Esc`, clears the
selection.

| Key | Action |
|-----|--------|
| `Shift`+arrows | Extend the selection by one cell |
| `Shift+Home` / `Shift+End` | Extend the selection to the first or last row (tracker) or position (order) |
| `Ctrl+A` | Select the whole frame, or the whole order |
| `Ctrl+Shift+A` | Select your column (tracker), or your channel's row (order) |
| `Ctrl+Alt+A` | Select the part of the column the cursor is in (tracker) |
| `Ctrl+C` | Copy |
| `Ctrl+X` | Cut |
| `Ctrl+V` | Paste at the cursor |
| `Del` | Empty the selection |

With nothing selected, copy, cut, paste and delete work on the cell under the cursor. The same
commands are on each grid's right-click menu. Right-click inside a selection to use them on the
whole selection.

Each grid has its own copy. A block copied in the tracker pastes into the tracker, and a block
copied in the order pastes into the order.

A paste starts at the cursor and fills down and to the right:

- In the **Tracker**, each cell keeps its kind. A volume pastes into a volume column, wherever you
  paste. Cells past the last row or column are dropped.
- In the **Order**, a paste past the last frame adds frames to the song. A paste stops at the
  **Noise** row.

Emptying cells keeps the rows and frames.

A copy also goes to your clipboard as text. You can paste a block into another open window of
_SampleToNES_, or into a message. Voices are copied by their number in the **Voices** list, so in
another project the block plays the voices with those numbers.

## Transpose and volume

In the **Tracker**, transpose and volume keys change every cell in the selection.

| Key | Action |
|-----|--------|
| `Ctrl+Up` / `Ctrl+Down` | Transpose by a semitone |
| `Ctrl+Shift+Up` / `Ctrl+Shift+Down` | Transpose by an octave |
| `Alt+Up` / `Alt+Down` | Change the volume by one step |
| `Alt+Shift+Up` / `Alt+Shift+Down` | Change the volume by four steps |

With nothing selected, the keys change the cell under the cursor. The same commands are on the
right-click menu.

## Undoing a change

You can undo every change, including a copy, a paste or a delete, which each count as one step. The
**History** panel lists your changes, and you can click one to go back to that point. **Undo** and **Redo** are
on the **Edit** menu.

## Timing and properties

**Module options** sets the song's timing: **Rows** per pattern, **Speed** (the number of [ticks](../glossary.md#tick)
each row lasts), **Tempo**, and the **NES frequency** the song plays at. Speed and tempo together set how fast
the rows go by. If the project has voices, changing **NES frequency** changes how they play, so the
app asks **Change NES frequency** first. Check **Don't ask again** to skip the question.

**File ▸ Project properties...** sets the title, the author and the comment. The exported module
includes them. It also sets the [meter](../glossary.md#metric-highlight):

- **First highlight** is the number of rows in a beat.
- **Second highlight** is the number of rows in a bar.

The tracker marks the first row of each beat and each bar. The defaults, 4 and 16, give four beats
of four rows in a bar. For waltz time, set **Second highlight** to 12, which gives three beats.

The tempo counts beats, so the meter also changes how fast the song feels. [Tempo as a
groove](../formats/bitphase.md#d-tempo-as-a-groove) explains how the app spreads a tempo over the
rows.

## Exporting the song

**File ▸ Export** writes the song in three formats:

- **FamiTracker module...** saves an `.ftm` file. See [FamiTracker
  export](../formats/famitracker.md) for its contents and limits.
- **Bitphase project...** saves a `.btp` file.
- **NSF program...** saves an `.nsf` file, which the NES or an NSF player plays directly.

An NSF program has room for 32 KB, so the app tells you when a song is too long. See [NSF
export](../formats/nsf.md) and [song compression](../concepts/compression.md).

**NSF program...** opens the **Export NSF program** window. Click **Export** without changing
anything to save the whole song, repeating from the start.

| Setting | What it does |
|---------|--------------|
| **Title**, **Artist**, **Copyright** | The text an NSF player shows. Each one holds 31 bytes |
| **Channels** | The channels the program plays. A channel you clear stays silent. Select at least one |
| **Repeat** | **Play once** stops at the end. **From the start** plays the song again. **From a frame** goes back to the order frame you type in **Frame** |
| **Level** | How much the song is compressed. **None** exports fastest and makes the largest file. **Full search** is the slowest and makes the smallest file |

**Export** closes the window and shows the export's progress.

## Rendering to audio

**File ▸ Render song...** (`Ctrl+Shift+E`) saves the whole song as an audio file that any player
opens.

| Setting | What it does |
|---------|--------------|
| **Format** | **WAV** for full quality, **MP3** for a smaller file |
| **Sample rate** | Samples per second. 44100 Hz is the usual choice |
| **Bit depth** (WAV) | How much detail each sample carries. 16-bit is the usual choice; 8-bit sounds rougher, like the NES |
| **Bitrate** (MP3) | How much data a second of audio takes. A higher bitrate sounds better and makes a larger file. The choices depend on the sample rate |
| **Normalize peak** | Makes the song louder until its loudest moment reaches full volume, keeping the balance between channels |

**Length** shows how long the file will be. Click **Render** to start. **Cancel** stops the render
and saves no file. When the render finishes, click the path to open its folder.

A render plays the song once, with every channel, whatever you muted or looped. A render, a conversion
and a library build run one at a time, and each waits for the one before it.
