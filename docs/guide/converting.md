# Converting audio

The **Main** tab (`F1`) turns audio files into [reconstructions](../concepts/reconstruction.md). You
gather the recordings you want on the **Converter** card, decide whether each one becomes its own
reconstruction or they all mix into one, choose which NES channels each recording may use, and start
the conversion.

## Choosing what to convert

The **Converter** card lists the recordings a conversion uses. Add them from the **Filesystem**
browser:

- Double-click an audio file, or Ctrl-click it, to add it. You can also right-click it and choose
  **Add as stem** — a *stem* is one recording that goes into a reconstruction.
- Ctrl-click a folder, or right-click it and choose **Add folder**, to add every recording inside it,
  at any depth in the folder tree.

Turn on **Playback ▸ Autoplay** (`Ctrl+P`) to play a recording with a single click. This lets you
listen through a folder before adding anything from it. With Autoplay off, right-click a recording and
choose **Play**.

Adding a folder opens a small window while the app reads the folder. **Stop** ends the search and
keeps the list as it was. If the folder has no recordings, the window says so and the list stays the
same.

**x** removes a row from the list. Removing a folder removes every recording in it.

Click a row to select it, and the **Source settings** card shows that recording. Right-clicking a row
selects it as well. Press `Del` to remove the selected row.

## One reconstruction each, or one mix from all

**Output**, at the top of the **Converter** card, sets what the conversion makes:

- **One per recording** — each recording in the list becomes its own reconstruction. Recordings added
  with a folder are saved in a matching folder structure.
- **One from all** — all recordings are mixed into a single reconstruction. Folders are replaced by
  the recordings inside them.

A mix can hold up to eight recordings. If you switch to **One from all** with more than eight
recordings in the list, a dialog asks which ones to mix. The same dialog opens when you add a folder
with more recordings than the mix has room for. Double-click a row in the dialog to hear the
recording. When the mix is full, uncheck a recording before you check another one.

When a mix has two or more recordings, the rows are grouped into **levels**. Levels set which
recordings get their channels first: recordings on level 1 get channels before recordings on level 2.
This lets a lead melody take the channels it needs before a background part does.

Drag a row onto another row to put them on the same level. Drag it into the gap between levels to give
it a level of its own. You can also right-click a row to use the same commands.

**Order** sets how the levels take turns:

- **Round robin** — every level gets a turn in each round.
- **Strict** — one level gets all its channels before the next level chooses.

## Choosing which channels a recording uses

The NES has four sound [channels](../glossary.md#channel): **Pulse 1**, **Pulse 2**, **Triangle** and
**Noise**. Every recording in the list has a checkbox for each channel. Check the channels that the
recording may use. Press `1` to `4` to switch a channel on or off for the selected row.

A folder's checkboxes stand for every recording inside it: checked where they all use the channel,
filled with the channel's color where only some do, and empty where none do. Clicking one changes the
channel for all of them. To change one recording on its own, open the folder first — click the marker
next to the folder name, or double-click the name — and each recording inside has its own checkboxes.

## Settings for one recording

The **Source settings** card sets how the recording you selected uses its channels. It has one line
per channel:

- **on** repeats the checkbox in the list, so you can also switch a channel there.
- **bend** tunes each note to the recording's exact pitch. **Pulse 1**, **Pulse 2** and **Triangle**
  have it; noise has none.
- **drive** sets how hard the recording pushes that channel. `1.00` is the level the recording was
  measured at, and up to `5.00` pushes it harder, which suits a part that sits quietly under the
  others. Drag the slider, or Ctrl-click it to type a value.

**Channels at once**, below the lines, sets how many of its channels the recording may sound in a
single frame. Set it to 1 to hear the recording on one channel at a time. It never sounds more
channels than it uses.

A folder shows what the recordings inside it agree on and reads **mixed** where they differ. Changing
anything settles every recording in the folder on it.

With no row selected, the card reads **New recordings** and holds the settings every recording you add
starts with. The app remembers them between sessions.

## Running a conversion

Click the button under **Output** to start the conversion. Its label says what it is about to do, and
reads **Cancel** while the conversion runs. Only one conversion runs at a time.

**Destination:** shows where the result is saved: a single file for one conversion, or a folder for a
longer run. Click the path to open it in your file manager. If the conversion would replace an
existing reconstruction, the app asks you first.

When the conversion finishes, click **Load** to open the result on the **Reconstruction** tab, where
you can [listen to it and export it](reconstruction.md). After a conversion of several recordings, the
button opens the folder instead.

The first conversion with new settings builds the [instruction
library](../concepts/instruction-library.md) for those settings, which takes a while. Later
conversions with the same settings use the library again.

## Building a library yourself

The **Instructions** tab (`F4`) builds and browses the [instruction
library](../concepts/instruction-library.md), the catalog of NES tones that a conversion searches. A
conversion builds the library it needs by itself, so you rarely need this tab. Use it to build a
library before a long session, or to explore the sounds your settings can make.

**Generate library** builds a library for your current settings. A library marked **[!]** was built by
another version of _SampleToNES_; click it to rebuild it.

Select an instruction to see its **Waveform** and **Spectrum**. This lets you see and hear a single
NES tone on its own. Click the waveform to play the tone from that point.
