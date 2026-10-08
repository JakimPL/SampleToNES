# Working with a reconstruction

The **Reconstruction** tab (`F2`) is where you listen to a
[reconstruction](../glossary.md#reconstruction), compare it against the audio it was made from, edit
the instruments it plays, and export it. Open one from the **Browser**, or click **Load** after [a
conversion](converting.md) on the **Main** tab.

## Listening to a reconstruction

The **Browser** groups reconstructions in two ways:

- **By configuration** groups them by the settings they were made with.
- **By sample** groups every version of the same source audio together.

To keep frequently used reconstructions within reach, right-click a reconstruction or a folder and
choose **Mark as favorite**. Check **Favorites only** to show only those items.

Opening another reconstruction while the open one has unsaved changes asks you to **Save** or
**Discard** them.

The **Source** card switches playback between **Reconstruction** and **Original audio**, so you can
compare the two. Type a new rate in **NES frequency** and press `Enter` to change the reconstruction's speed. A
reconstruction that belongs to a project follows the project's rate, so the field is locked. Save it to
a file to unlock the field.

Keys `1` to `4` switch the channels of the **Waveform** card. `Ctrl+1` to `Ctrl+4` work while you
type in a field.

On the waveform:

- Click to play from that point, or to move the playback position while paused.
- Drag to move the view.
- Double-click to show the whole waveform.
- Scroll to zoom. Hold **Alt** and scroll to move sideways, or **Alt** and **Shift** to move up and
  down.

## Hearing what each recording contributed

The **Stems** card lists the recordings a reconstruction was built from, grouped by the
[level](converting.md#one-reconstruction-each-or-one-mix-from-all) each one was given. A row has a
checkbox for each channel the recording used, and the checkbox at the front switches all of them.
Double-click a row to show the recording in your file browser. Right-click a row to **Mute** the
recording, hear it alone with **Solo**, or copy its name or path.

Uncheck a box to hear the reconstruction without that recording on that channel. The waveform,
playback and WAV export follow the checkboxes.

The colored bars under the waveform show which recording played each stretch of each channel.

The **Instruments** panel shows and edits only the recordings you have checked. To change one
recording's part of a channel, uncheck the others first.

Notes you write where no recording played go to an **Edits** row.

**x** at the end of a row removes that recording, after you confirm.

## Editing instruments

The **Instruments** panel shows what each channel plays, as one
[sequence](../glossary.md#sequence-envelope) per dimension. Edit a sequence by dragging its bars or typing values.

Each channel has its own set:

- **Pulse 1** and **Pulse 2** — volume, arpeggio, pitch, hi-pitch and [duty
  cycle](../glossary.md#duty-cycle).
- **Triangle** — volume, arpeggio, pitch and hi-pitch.
- **Noise** — volume, arpeggio and duty cycle.

Type `|` before a value to mark where the sequence repeats while a note is held. `15 14 | 12 10` plays
the attack once and then loops the last two values.

A sequence that is too long for an export is marked. Point at it to see how many values each export
keeps.

Clear a sequence to play its default on every note. An empty volume sequence plays at the volume the
pattern sets. An empty arpeggio, pitch or hi-pitch sequence keeps the note where the pattern puts it. An
empty duty cycle sequence plays duty 0 on a pulse channel and the long mode on noise.

You can also edit an [**instrument**](../glossary.md#instrument) here: right-click it in the
**Voices** list and choose **Edit**. See [voices](sequencer.md#voices-samples-and-instruments).

For an instrument, **Audition** lets you choose **Pulse**, **Triangle** or **Noise** and play the
instrument on that channel with the note keys.

## Exporting

You export a reconstruction from the **Reconstruction** menu:

- **Export instruments ▸ FamiTracker instruments...** writes one `.fti` file per channel.
- **Export instruments ▸ Bitphase presets...** writes the same instruments as `.json`.
- **Export instruments ▸ NSF program...** opens the **Export NSF program** window and writes a single
  `.nsf` file that plays the whole reconstruction on a NES. The window is described [in the
  sequencer guide](sequencer.md#exporting-the-song).
- **Export to WAV...** renders the audio using the channel and recording checkboxes you have set.

**Export instrument...** in the **Instruments** panel writes the channel you are looking at, in the
format you choose in the save dialog. See [where your files
live](files.md#naming-exported-files).

To use a reconstruction in a song, right-click it and choose **Add to Sequencer**.
