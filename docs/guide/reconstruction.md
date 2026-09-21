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

If the reconstruction you have open has unsaved changes, opening another one asks whether to save it
first.

The **Source** card switches playback between **Reconstruction** and **Original audio**, so you can
compare the two. The **Waveform** card has a checkbox for each channel, and keys `1` to `4` switch the
same checkboxes.

Click the waveform to play from that point. While playback is paused, a click moves the playback
position. Drag the waveform to move the view, and double-click to fit the view.

## Hearing what each recording contributed

The **Stems** card lists the recordings a reconstruction was built from, grouped by the
[level](converting.md#one-reconstruction-each-or-one-mix-from-all) each one was given. A row has a
checkbox for each channel the recording used, and the checkbox at the front switches all of them.
Double-click a row to show the recording in your file browser. Right-click a row to **Mute** the
recording, hear it alone with **Solo**, or copy its name or path. **Unsolo** brings back the mix you had.

Uncheck a box to hear the reconstruction without that recording on that channel. The waveform, the
playback, the original audio and a WAV export all follow the checkboxes, so you can hear what each
recording added, channel by channel. The saved reconstruction keeps every channel, whatever you
uncheck.

Each recording has a color. The bars under the waveform use it to show which recording played each
stretch of each channel.

The **Instruments** panel follows the same checkboxes. It shows only what you have checked, its sizes
measure only that, and an edit changes only that. To reshape one recording's part of a channel, uncheck the others first.

Notes you write where no recording played gather in an **Edits** row, which has checkboxes of its own.
Removing a recording leaves them alone.

**Collapse levels** shows the whole list as one table.

**x** at the end of a row removes that recording, after you confirm. The change is saved when you save
the reconstruction. The **x** of the last recording is disabled, because a reconstruction needs at least
one. The **Edits** row has no **x**.

## Editing instruments

The **Instruments** panel shows what each channel plays, as one
[sequence](../glossary.md#sequence-envelope) per dimension. A colored band beneath each set of bars
shows which recording each frame came from. Edit a sequence by dragging its bars or typing values.

Each channel has its own set:

- **Pulse 1** and **Pulse 2** — volume, arpeggio, pitch, hi-pitch and [duty
  cycle](../glossary.md#duty-cycle).
- **Triangle** — volume, arpeggio, pitch and hi-pitch.
- **Noise** — volume, arpeggio and duty cycle.

Type `|` before a value to mark where the sequence repeats while a note is held. `15 14 | 12 10` plays
the attack once and then loops the last two values.

Clear a sequence to use the channel's own setting. For example, an instrument with an empty volume
sequence plays at the volume the channel is set to. Each channel shows how many bytes its instrument
takes on the NES, so you can see how much space an edit uses.

You can edit an [**instrument**](../glossary.md#instrument) here as well. It is a voice you write by
hand, described in the [sequencer guide](sequencer.md#voices-samples-and-instruments). Right-click one
in the **Voices** list and choose **Edit**.

For an instrument, the panel shows **Audition** in place of the pitch steppers. Choose **Pulse**,
**Triangle** or **Noise**, and the note keys play the instrument on that channel.

## Exporting

You export a reconstruction from the **Reconstruction** menu:

- **Export instruments ▸ FamiTracker instruments...** writes one `.fti` file per channel.
- **Export instruments ▸ Bitphase presets...** writes the same instruments as `.json`.
- **Export instruments ▸ NSF program...** opens the **Export NSF program** window and writes a single
  `.nsf` file that plays the whole reconstruction on a NES. The window matches the one [in the
  sequencer](sequencer.md#exporting-the-song), except that **Repeat** has no **From a frame** and
  **Level** has no **Samples**. You can select the channels the reconstruction uses.
- **Export to WAV...** renders the audio using the channel and recording checkboxes you have set.

Every export writes what you see and hear. The instrument files hold the same part of each channel that
the **Instruments** panel shows.

**Export instrument...** in the **Instruments** panel writes only the channel you are looking at, in
whichever format you choose in the save dialog. See [where your files
live](files.md#naming-exported-files).

To use a reconstruction in a song, right-click it and choose **Add to Sequencer**.
