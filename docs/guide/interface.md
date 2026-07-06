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
When a single file finishes, **Load** opens the result on the **Reconstructions**
tab; **Cancel** stops a run, and only one runs at a time.

The settings worth knowing before you convert: under **Reconstructor settings**,
the **Generators** toggles choose which channels take part (at least one must be
on) and **Drive** sets how hard they are pushed; the analysis options — sample
rate, NES frequency, generation method, and feature scaling — live in **General
settings**. Less-common options, including the worker count and the output and
library folders, sit under **Advanced settings**, which **View ▸ Show advanced
settings** reveals. [Configuration](configuration.md) explains what each one does.

## Reconstructions

The **Reconstructions** tab is where you audition a reconstruction against the
original, fine-tune it, and export it.

Open a saved reconstruction from the list on the left; if the current one has
unsaved edits, you are asked whether to save it first. You can play it back and
switch **Play audio source:** between **Reconstruction** and **Original audio** to
compare the two, and **Locate original audio** re-links the source file if it has
moved. To get your results out, **Export FamiTracker instruments** writes one
`.fti` per channel, **Export reconstruction to WAV** renders the audio, and **Add
to Sequencer** sends the reconstruction into a song as a sample (see the
[sequencer guide](sequencer.md)).

For finer control, the **Instruments** panel on the right shows each channel's
instrument — its pitch, volume, arpeggio, and duty sequences — which you can edit
by dragging the bars or typing values, and export one channel at a time.

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

The **File** menu manages projects — new, open, save, properties, close, and
**Export FamiTracker module...**. **Edit** holds **Undo** and **Redo**.
**Reconstruction** gathers everything for the current reconstruction: reconstruct,
open, save, and the export actions. **Playback** controls play, pause, and stop and
opens **Audio settings...**. **View** toggles **Show advanced settings** and
**Fullscreen**, and **Help** has **About**.

**Audio settings** (**Playback ▸ Audio settings...**) choose the playback device,
sample rate, and buffer size. These affect playback only — they are separate from
the **Sample rate** and **NES frequency** on the **Main** tab, which govern how
audio is reconstructed.

Project properties belong to a project and are covered in the
[sequencer guide](sequencer.md).
