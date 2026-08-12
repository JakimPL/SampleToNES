# The interface

_SampleToNES_ is a single window: a menu bar at the top, four tabs, and a status
bar along the bottom. Within a tab, work generally flows left to right — you pick
something on the left, act on it in the centre, and inspect or refine it on the
right.

This page covers the **Main**, **Instructions**, and **Reconstructions** tabs and
the menus around them. The **Sequencer** has [its own page](sequencer.md).

## Main

The **Main** tab turns an audio file into a
[reconstruction](../concepts/reconstruction.md), and it is where most sessions
begin.

Pick an audio file — or a whole folder — in the **Filesystem** browser on the
left, set up how the reconstruction is done in the centre, and click **Convert
sample** (or **Convert directory** for a folder). The
[instruction library](../concepts/instruction-library.md) for your settings is
built automatically the first time it is needed, so you can convert straight away.
While it runs, the panel names the file going in and where the result is going, and
clicking either path shows it in your file manager. When a single file finishes,
**Load** opens the result on the **Reconstructions** tab; **Cancel** stops a run, and
only one runs at a time.

A few settings are worth knowing before you convert. Under **Reconstructor
settings**, the **Generators** toggles choose which channels take part — at least
one must be on — and **Drive** sets how hard they are pushed. **General settings**
holds the analysis options: sample rate, NES frequency, generation method, and
feature scaling. The rest, including the worker count and the output and library
folders, sit under **Advanced settings**, which **View ▸ Show advanced settings**
reveals. [Configuration](configuration.md) explains each one.

## Reconstructions

The **Reconstructions** tab is where you audition a reconstruction against the
original, fine-tune it, and export it.

Open a saved reconstruction from the list on the left; if the current one has
unsaved edits, you are asked whether to save it first. You can play it back and
switch **Play audio source:** between **Reconstruction** and **Original audio** to
compare the two, and **Locate original audio** re-links the source file if it has
moved.

To get your results out, use the **Reconstruction** menu. **Export instruments ▸
FamiTracker instruments...** writes one `.fti` per channel, **Bitphase
presets...** writes the same as `.json`, and **Export to WAV...** renders the
audio. To use the reconstruction in a song, right-click it and choose **Add to
Sequencer** (see the [sequencer guide](sequencer.md)).

For finer control, the **Instruments** panel on the right shows each channel's
instrument — its pitch, volume, arpeggio, and duty sequences — which you can edit
by dragging the bars or typing values. **Export instrument...** writes the channel
on show, for whichever tracker the save dialog's file type names — see
[where your files live](files.md#exported-files).

## Instructions

The **Instructions** tab generates and browses the
[instruction library](../concepts/instruction-library.md) for your current
settings, and lets you inspect individual instructions.

You will rarely come here just to build a library — reconstructing on the **Main**
or **Reconstructions** tab builds the matching one automatically. It earns its
place for building one ahead of time, or for exploring what a configuration can
produce: pick an instruction and its waveform and spectrum appear with a player,
so you can hear a single NES tone on its own. Click **Generate library** to build
the library for the current settings (if one already exists, _SampleToNES_ asks
**Regenerate library?**), **Cancel generation** to stop, and **Refresh
instructions data** to re-read the catalogue; selecting an entry in the
**Libraries** tree loads it.

## Around the app

The menu bar and status bar sit outside the tabs.

Each menu covers one kind of work: **File** for projects, **Edit** for undo, redo,
and what you can do where your cursor stands, **Reconstruction** for the current
reconstruction and its exports, **Playback** for playing and for muting the
sequencer's channels, **View** for settings and the window, and **Help** for
**About**.

Two items write audio you can play anywhere: **Reconstruction ▸ Export to WAV...**
for the reconstruction on show, and **File ▸ Render song...** (`Ctrl+Shift+E`) for
the sequencer's whole song, as a WAV or an MP3 —
[rendering to audio](sequencer.md#rendering-to-audio) covers the options it offers.

Two other items are easy to miss. **View ▸ Show advanced settings** reveals the extra
options on the **Main** tab. **Playback ▸ Audio settings...** picks the playback
device, sample rate, and buffer size; these change what you hear, while the
**Sample rate** and **NES frequency** on the **Main** tab change how audio is
reconstructed.

`F1` to `F4` toggle the four NES channels on the tab in front of you: the
generators on **Main**, the channels drawn on **Reconstructions**, and the song's
mix on the **Sequencer**.

### Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists everything you can do from the
keyboard and lets you change any of it. Click an action's shortcut and press the
keys you want, or type them into the box below the list. If another action already
uses those keys, the app names it and asks whether to hand them over. **Reset to
defaults** puts everything back, and your changes take effect when you press
**OK**.

On macOS the shortcuts use Command where other platforms use Control. What you
change is saved with your settings and is there the next time you start.

Project properties belong to a project and are covered in the
[sequencer guide](sequencer.md).
