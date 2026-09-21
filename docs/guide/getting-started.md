# Getting started

This page shows two quick ways to start: turning a sound into FamiTracker instruments, and building
a song. First, [install](installation.md) _SampleToNES_.

## Reconstruct a sound into FamiTracker instruments

1. Launch the app and open the **Main** tab.
2. In the **Filesystem** browser, double-click an audio file, for example `Kick.wav`. WAV, MP3, FLAC,
   OGG, AIFF and AU files work. To reconstruct every audio file in a folder, Ctrl-click the folder
   instead.
3. Optional: click the recording in the list and check the channels it may use under **Source
   settings**. Each recording needs at least one channel.
4. Optional: change **General settings**, such as the sample rate.
5. Click the button under **Output** to start the conversion. The first conversion with a new set of
   settings takes longer, because the [instruction library](../concepts/instruction-library.md) it
   needs is built first.
6. When it finishes, click **Load** to open the result on the **Reconstruction** tab.
7. Choose **Reconstruction ▸ Export instruments ▸ FamiTracker instruments...** and name the export
   `Kick`. The app writes one `.fti` file per channel: `Kick (pulse1).fti`, `Kick (triangle).fti`,
   and so on.

That is the shortest path from a sound to instruments you can load in FamiTracker.
[Converting audio](converting.md) and [working with a
reconstruction](reconstruction.md) cover the **Main** and **Reconstruction** tabs
in full.

## Build a song and export a module

1. Choose **File ▸ New project**. The app switches to the **Sequencer** tab.
2. Have one or more reconstructions ready — make them as above, or open existing
   ones.
3. Add each as a [sample](../glossary.md#sample-sequencer): in the Sequencer's **Browser**, right-click a
   reconstruction and choose **Add to Sequencer**. If its NES frequency differs
   from the project's, confirm with **Add anyway**.
4. In the **Tracker** grid, click a cell and type notes on your keyboard. To
   assign a sample to a channel, right-click a cell and choose **Set voice**.
5. Arrange the piece in the [**Order**](../glossary.md#order) grid. Under **Module options**, set
   **Rows** (the length of a pattern), **Speed** (the [ticks](../glossary.md#tick) each row lasts),
   **Tempo** and **NES frequency**.
6. Choose **File ▸ Export ▸ FamiTracker module...** and pick a path for the `.ftm`
   file. **Bitphase project...** next to it writes the same song as a `.btp`.

The [sequencer guide](sequencer.md) covers the tracker grid, the order, voices,
and undo history in full.
