# The sequencer

The **Sequencer** tab (`F3`) is a tracker. You use it to arrange voices into a song on the four NES
channels. You can export the song as a FamiTracker [module](../formats/famitracker.md) (`.ftm`),
play it back, or render it to audio.

The sequencer works on a [project](../formats/projects.md). Choose **File ▸ New project** to start
one, or open an existing `.stp` file.

## Voices: samples and instruments

A song plays **voices**. There are two kinds:

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

The first three items are also at the top of the **Voices** list. Right-click below the rows of
the list to open the same menu.

**Add to Sequencer** is also on the **Reconstruction** tab. On the Sequencer tab, right-click a
reconstruction in the **Browser** to find it.

If a reconstruction uses a different NES frequency than the project, the app shows **Different
NES frequency**. Click **Add anyway** to add it.

To change how a new instrument sounds, right-click it and choose **Edit**. The instrument opens on
the **Reconstruction** tab. See [editing instruments](reconstruction.md#editing-instruments).

An imported `.fti` file keeps its volume, arpeggio and duty cycle sequences. **Instrument
imported** lists any other settings of the file, which the instrument leaves out. See [reading an instrument
file](../formats/famitracker.md#c-reading-an-instrument-file).

A sample's right-click menu has **New instrument from**. Choose a channel to copy what the sample
plays on that channel into a new instrument you can edit.

Right-click any voice to use these commands:

- **Edit**, **Rename**, **Duplicate** and **Remove**.
- Commands that move the voice up or down the list.
- **Export instrument...**, which saves the voice as an `.fti` file. A sample has one instrument
  per channel, so the app asks which channel to export.

The **Edit** menu has the same commands for the voice you selected.

The right-click menu also shows how many bytes the voice takes on the NES. For a sample, it shows
the total and the size of each channel.

If patterns still use a voice, removing the voice asks you first. Removing it clears every row
that uses it.

Hover over a voice to see its name, its kind, its channels and its size.

## Writing a pattern

The **Tracker** grid is the pattern editor. Each row is one step in time. The grid has a
**Sample** column and a column for each channel: **Pulse 1**, **Pulse 2**, **Triangle** and
**Noise**. Each channel column has a voice, a pitch and a volume.

Click a cell and type its value.

Right-click a cell for more commands:

- **Set voice** chooses the voice for the cell.
- **Note off** stops the note.
- **Clear cell** and **Clear row** empty the cell or the whole row.
- Transpose and volume commands change the pitch and volume.
- **Play from here** plays from the row you clicked.
- **Play from this frame** plays from the top of the frame on screen.

The **Sample** column places a sample on every channel the sample uses, and clears the other
channels of the row. The **Sample** column takes samples only. To place an instrument, use the
column of the channel you want it on.

A `?` in the **Sample** column means the channels of that row play different voices.

## Typing a pitch

A pitch cell shows a number. What the number means depends on the voice:

- For a sample, the number is a step from the pitch the sample was recorded at. `+00` plays the
  sample as recorded. `+0C` plays it one octave higher.
- For an instrument, the number is a note, such as `C-4` or `A#3`.

Type notes on your keyboard like a piano:

- The bottom two rows of keys play one octave: `Z` `S` `X` `D` `C` and so on.
- The two rows above them play the next octave: `Q` `2` `W` `3` `E` and so on.

**Octave**, above the grid, sets the octave of the bottom row. The same keys work in a sample's
cell and type the step that plays the note you pressed.

The noise channel has sixteen sounds in place of notes. Type a noise cell as a signed step, such as
`+03` or `-02`.

## Arranging the song

A song plays patterns in a sequence. The **Order** grid sets that sequence. Each column is one
position in the song. The grid has a row for the **Master** and a row for each channel.

Type a pattern number in the **Order** grid to place a pattern. Right-click a frame for more
commands:

- **Duplicate** repeats the frame with the same patterns.
- **Clone** repeats the frame with new copies of its patterns, so you can change them separately.
- **Insert frame**, **Clear frame** and **Remove** add, empty and delete frames.
- **Play from this frame** plays from that frame.

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
| `Ctrl+Alt+A` | Select your subcolumn (tracker) |
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
  paste. Cells past the last row or column are dropped. A `?` cell leaves the target cell as it
  was.
- In the **Order**, a paste past the last frame adds frames to the song. A paste stops at the
  **Noise** row.

Emptying cells keeps the rows and frames. Every copy, cut, paste and delete is one step in the
history, so one **Undo** reverses it.

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

## Playing the song

The transport under the grid plays the song. These keys work anywhere on the tab:

| Key | Action |
|-----|--------|
| `Space` | Play, or pause and resume |
| `Shift+Space` | Play from the start |
| `Ctrl+Space` | Play from the frame on screen |
| `Ctrl+Shift+Space` | Play from the cursor's row |
| `Esc` | Stop |
| `Ctrl+L` | **Loop song**: start the song again when it ends |

`Esc` also stops a sample preview. The same commands are on the **Playback** menu.

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

Click a channel's name at the top of the tracker to mute the channel. Click the name again to
unmute it. The channel names in the **Order** grid work the same way.

| Gesture | Action |
|---------|--------|
| Click a channel's name | Mute or unmute the channel |
| `Ctrl`+click a channel's name | Solo the channel. `Ctrl`+click again to restore the previous mix |
| Click **Sample** (tracker) or **Master** (order) | Mute or unmute every channel |
| Right-click a name | The same commands as a menu |

**Playback ▸ Channels** shows which channels play. **Unmute all channels** unmutes all four. Keys
`1` to `4` mute and unmute a channel when the cursor is outside the grids. Inside the grids, the
digit keys type values.

Muting changes only what you hear. Saving, exporting, rendering and undo use every channel. Opening,
creating or closing a project unmutes all channels.

## Timing and properties

**Module options** sets the song's timing: **Rows** per pattern, **Tempo**, **Speed** and **NES
frequency**. If the project has voices, changing **NES frequency** changes how they play, so the
app asks **Change NES frequency** first. Check **Don't ask again** to skip the question.

**File ▸ Project properties...** sets the title, the author and the comment. The exported module
includes them.

**Project properties** also sets the meter:

- **First highlight** is the number of rows in a beat.
- **Second highlight** is the number of rows in a bar.

The tracker marks the first row of each beat and each bar. The defaults, 4 and 16, give four beats
of four rows in a bar. For waltz time, set **Second highlight** to 12, which gives three beats.

The tempo counts beats, so the meter also changes how fast the song feels. [Tempo as a
groove](../formats/bitphase.md#d-tempo-as-a-groove) explains how the app spreads a tempo over the
rows.

## Undo and export

You can undo every change. The **History** panel lists your changes. **Undo** and **Redo** are also
on the **Edit** menu. Click a change in the **History** panel to go back to that point.

To export the song:

- **File ▸ Export ▸ FamiTracker module...** saves an `.ftm` file. See [FamiTracker
  export](../formats/famitracker.md) for its contents and limits.
- **File ▸ Export ▸ Bitphase project...** saves a `.btp` file.
- **File ▸ Export ▸ NSF program...** saves an `.nsf` file, which the NES or an NSF player plays
  directly. An NSF program has room for 32 KB, so the app tells you when a song is too long. See [NSF
  export](../formats/nsf.md) and [song compression](../concepts/compression.md).

## Exporting an NSF program

**File ▸ Export ▸ NSF program...** opens the **Export NSF program** window. Click **Export** without
changing anything to save the whole song, repeating from the start.

| Setting | What it does |
|---------|--------------|
| **Title**, **Artist**, **Copyright** | The text an NSF player shows. Each one holds 31 bytes |
| **Channels** | The channels the program plays. A channel you clear stays silent. Select at least one |
| **Repeat** | **Play once** stops at the end. **From the start** plays the song again. **From a frame** goes back to the order frame you type in **Frame**, numbered as in the order list |
| **Level** | How much the song is compressed. **None** exports fastest and makes the largest file. **Full search** is the slowest and makes the smallest file |
| **File** | Where the file is saved. **Browse...** opens the save dialog |

**Export** closes the window and shows the export's progress.

## Rendering to audio

**File ▸ Render song...** (`Ctrl+Shift+E`) saves the whole song as an audio file that any player
opens.

| Setting | What it does |
|---------|--------------|
| **Format** | **WAV** for full quality, **MP3** for a smaller file |
| **Sample rate** | Samples per second. 44100 Hz is the usual choice |
| **Bit depth** (WAV) | 16-bit PCM is the usual choice. 8-bit sounds rougher, like the NES |
| **Bitrate** (MP3) | A higher bitrate sounds better and makes a larger file. The choices depend on the sample rate |
| **Normalize peak** | Makes the song louder until its loudest moment reaches full volume, keeping the balance between channels |
| **File** | Where the file is saved. **Browse...** opens the save dialog. Click the path to open its folder |

**Length** shows how long the file will be. Click **Render** to start. **Cancel** stops the render
and saves no file. When the render finishes, click the path to open its folder.

A render plays the song once, with every channel, whatever you muted or looped. While a render
runs, conversions and library builds wait, and a render waits for them in the same way.
