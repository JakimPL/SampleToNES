# Getting started

Two quick paths through _SampleToNES_: turning a sound into FamiTracker
instruments, and building a whole song. Both assume it is already
[installed](installation.md).

## Reconstruct a sound into FamiTracker instruments

1. Launch the app and open the **Main** tab.
2. In the **Filesystem** browser, double-click an audio file (WAV, MP3, FLAC,
   OGG, AIFF, or AU) — or Ctrl-click a folder, to reconstruct every audio file
   inside it.
3. Optionally click the recording in the list and choose which channels it uses
   under **Source settings**, and adjust **General settings**. Each recording
   needs at least one channel.
4. Click the button under **Output** to start the conversion. The first time you
   convert with a given set of settings, the [instruction
   library](../concepts/instruction-library.md) it needs is built first
   ("Generating instructions library..."), which takes a while.
5. When it finishes, click **Load** to open the result on the **Reconstruction**
   tab.
6. Choose **Reconstruction ▸ Export instruments ▸ FamiTracker instruments...** and
   name the export. The app writes one `.fti` file per instrument: `Kick
   (pulse1).fti`, `Kick (triangle).fti`, and so on.

That is the shortest path from a sound to instruments you can load in FamiTracker.
[Converting audio](converting.md) and [working with a
reconstruction](reconstruction.md) cover the **Main** and **Reconstruction** tabs
in full.

## Build a song and export a module

1. Choose **File ▸ New project**. The app switches to the **Sequencer** tab.
2. Have one or more reconstructions ready — make them as above, or open existing
   ones.
3. Add each as a sample: in the Sequencer's **Browser**, right-click a
   reconstruction and choose **Add to Sequencer**. If its NES frequency differs
   from the project's, confirm with **Add anyway**.
4. In the **Tracker** grid, click a cell and type notes on your keyboard. To
   assign a sample to a channel, right-click a cell and choose **Set voice**.
5. Arrange the piece in the **Order** grid, and set **Rows**, **Tempo**, **Speed**,
   and **NES frequency** under **Module options**.
6. Choose **File ▸ Export ▸ FamiTracker module...** and pick a path for the `.ftm`
   file. **Bitphase project...** next to it writes the same song as a `.btp`.

The [sequencer guide](sequencer.md) covers the tracker grid, the order, voices,
and undo history in full.
