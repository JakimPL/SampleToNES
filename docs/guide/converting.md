# Converting audio

The **Main** tab (`F1`) turns audio files into
[reconstructions](../concepts/reconstruction.md). You gather the recordings you
want on the **Converter** card, choose which NES channels each one may use,
decide whether every recording becomes its own reconstruction or they all mix
into one, and start the conversion.

## Choosing what to convert

The **Converter** card lists the recordings a conversion uses. Add them from the **Filesystem** browser:

- Double-click an audio file, or Ctrl-click it, to add it. You can also right-click it and choose **Add as stem**.
- Ctrl-click a folder, or right-click it and choose **Add folder**, to add every recording inside it, at any depth in the folder tree.

Turn on **Playback ▸ Autoplay** (`Ctrl+P`) to play a recording with a single click. This lets you listen through a folder before adding anything from it. With Autoplay off, right-click a recording and choose **Play**.

Adding a folder opens a small window while the folder is read. The window names the folder, counts the recordings found so far, and has a **Stop** button that gives up the search. A folder with no recordings inside it says so and adds nothing.

**x** removes a row from the list. Removing a folder removes every recording in it.

Click a row to pick it out. The **Source settings** card then shows that row. Click it again, or press `Esc`, to let it go. Press `Del` to remove the row you picked out.

## Choosing which channels a recording uses

The NES has four sound channels: **Pulse 1**, **Pulse 2**, **Triangle**, and **Noise**. Every recording in the list has a checkbox for each channel. Check the channels that the recording may use. Press `1` to `4` to switch a channel on or off for the row you picked out.

A folder represents all the recordings inside it. Its checkbox shows their channel assignments:

- checked if all recordings use the channel,
- filled with the channel's color if only some recordings use it,
- empty if none of them use it.

Click the checkbox to change the channel for all recordings in the folder. To change the channel for one recording, open the folder and click the marker next to its name, or double-click the recording name.

The **Source settings** card has two more settings. **Drive** sets how hard the channels are pushed. It applies to the whole conversion.

Below it, the card shows the name of the recording you selected in the list and a checkbox for each of its channels. **Pulse 1**, **Pulse 2**, and **Triangle** also have a **bend** checkbox. This tunes each note to the recording's exact pitch. Noise has no bend.

**Channels per source** limits how many channels one recording can use at the same time, from 1 to 4. Set it to 1 to make each recording use one channel.

## One reconstruction each, or one mix from all

**Output**, at the top of the **Converter** card, decides what the conversion produces:

- **One per recording** — each recording in the list becomes its own reconstruction. Recordings added with a folder are saved in a matching folder structure.
- **One from all** — all recordings are mixed into a single reconstruction. Folders are replaced by the recordings inside them.

A mix can hold up to eight recordings. If you switch to **One from all** with more than eight recordings in the list, a dialog asks which ones to mix. The same dialog opens when you add a folder with more recordings than the mix has room for.

The dialog lists the same rows as the card and shows how many recordings you have selected. Double-click a row to hear the recording. **Add** becomes available when your selection fits. A full mix cannot accept more recordings, so uncheck one before checking another.

Once a mix has two or more recordings, the rows are grouped into **levels**. A level decides which recordings choose their channels first. Everything on level 1 is given channels before anything on level 2. This lets a lead melody take the channels it needs before a background part does.

Drag a row onto another row to put them on the same level. Drag it into the gap between levels to give it a level of its own. You can also right-click a row to use the same commands.

**Order** decides how the levels take turns:

- **Round robin** — every level gets a turn in each round.
- **Strict** — one level is filled before the next one chooses.

## Running a conversion

Click the button under **Output** to start the conversion. The button's label tells you what it is about to do. Only one conversion can run at a time. While a conversion is running, the button reads **Cancel**.

**Destination:** shows where the result is saved: a single file for one conversion, or a folder for a longer run. Click the path to open it in your file manager. If the conversion would replace an existing reconstruction, the app asks you first.

When the conversion finishes, click **Load** to open the result on the **Reconstruction** tab, where you can [listen to it and export it](reconstruction.md). After a conversion of several recordings, the button reads **Open** instead.

The first conversion with a given set of settings builds the [instruction library](../concepts/instruction-library.md) it needs. This takes a while. Later conversions with the same settings reuse the library.

## The instruction library

The **Instructions** tab (`F4`) builds and browses the [instruction library](../concepts/instruction-library.md), the catalog of NES tones that a conversion searches.

A conversion builds the library it needs on its own, so you rarely need to go there. The tab is useful for building a library before a long session and for exploring what your settings can produce.

Select an instruction to see its **Waveform** and **Spectrum**. This lets you see and hear a single NES tone on its own.

**Generate library** builds a library for your current settings. Once a library is loaded, the button reads **Regenerate instructions**.
