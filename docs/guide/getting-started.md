# Getting started

Two quick paths through _SampleToNES_: turning a sound into FamiTracker
instruments, and building a whole song. Both assume it is already
[installed](installation.md).

## Reconstruct a sound into FamiTracker instruments

1. Launch the app and open the **Main** tab.
2. In the **Filesystem** browser on the left, click an audio file (WAV, MP3,
   FLAC, OGG, AIFF, or AU) — or a folder, to reconstruct every audio file inside it.
3. Optionally choose which channels to use under **Reconstructor settings** and
   adjust **General settings**. At least one generator must be enabled.
4. Click **Convert sample** (or **Convert directory** for a folder). The first
   time you use a given set of settings, the
   [instruction library](../concepts/instruction-library.md) is built
   automatically ("Generating instructions library..."), then the reconstruction
   runs.
5. When it finishes, click **Load** to open the result on the **Reconstructions**
   tab.
6. Click **Export FamiTracker instruments** and choose a folder. One `.fti`
   instrument is written per channel.

That is the shortest path from a sound to instruments you can load in FamiTracker.
The [interface guide](interface.md) covers the **Main** and **Reconstructions**
tabs in full.

## Build a song and export a module

1. Choose **File ▸ New project**. The app switches to the **Sequencer** tab.
2. Have one or more reconstructions ready — make them as above, or open existing
   ones.
3. Add each as a sample: in the Sequencer's **Reconstructions** browser on the
   left, right-click a reconstruction and choose **Add to Sequencer**. If its NES
   frequency differs from the project's, confirm with **Add anyway**.
4. In the **Tracker** grid, click a cell and type notes on your keyboard; assign a
   sample to a channel with the cell's right-click **Set instrument**.
5. Arrange the piece in the **Order** grid, and set **Rows**, **Tempo**, **Speed**,
   and **NES frequency** under **Module options**.
6. Choose **Export as FamiTracker module** (or **File ▸ Export FamiTracker
   module...**) and pick a path for the `.ftm` file.

The [sequencer guide](sequencer.md) covers the tracker grid, the order, samples,
and undo history in full.
