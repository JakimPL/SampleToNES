# Working with a reconstruction

The **Reconstruction** tab (`F2`) is where you listen to a reconstruction,
compare it against the audio it was made from, edit the instruments it plays,
and export it. Open one from the **Browser**, or click **Load** after
[a conversion](converting.md) on the **Main** tab.

## Listening to a reconstruction

Open a saved reconstruction from the **Browser** on the **Reconstruction** tab.

The browser groups reconstructions in two ways:

- **By configuration** groups them by the settings they were made with.
- **By sample** groups every version of the same source audio together.

If the reconstruction you have open has unsaved changes, the app asks whether to save it first.

To keep frequently used reconstructions within reach, right-click a reconstruction or a folder and choose **Mark as favorite**. Check **Favorites only** to show only those items.

The **Source** card switches playback between **Reconstruction** and **Original audio**, so you can compare the two. The **Waveform** card shows each channel and has a checkbox for each one. Keys `1` to `4` toggle the same checkboxes.

## Hearing what each recording contributed

The **Stems** card lists the recordings used to build a reconstruction. It groups them by the level each one was given. Every row has a checkbox for each channel that the recording used, and the checkbox at the front toggles all of them.

Uncheck a channel to silence it in the waveform, playback, original audio, and WAV export. This lets you hear what one recording contributed, channel by channel. These checkboxes only change what you hear. They do not change anything that is saved.

**Collapse levels** shows the whole list as one table.

**x** at the end of a row removes that recording from the reconstruction after asking you to confirm. The recording becomes silent and its row disappears, and the change is written when you save the reconstruction. A reconstruction keeps at least one recording, so the last row's **x** is disabled.

## Editing instruments

The **Instruments** panel shows what each channel plays. You edit the sequences by dragging the bars or typing values.

Each channel has its own set of sequences:

- **Pulse 1** and **Pulse 2** — volume, arpeggio, pitch, hi-pitch, and duty cycle.
- **Triangle** — volume, arpeggio, pitch, and hi-pitch.
- **Noise** — volume, arpeggio, and duty cycle.

Type `|` before a value to mark where the sequence repeats while a note is held. `15 14 | 12 10` plays the attack once and then loops the last two values.

Clear a sequence to leave that setting to the channel. For example, an instrument with an empty volume sequence plays at whatever volume the channel is set to. Each channel shows how many bytes its instrument takes on the NES, so you can see what an edit costs.

You can also edit a hand-written **instrument** here — a voice with no recording behind it, described in the [sequencer guide](sequencer.md#voices-samples-and-instruments). Right-click it in the **Voices** list and choose **Edit**.

Since an instrument has no recording, the panel shows **Audition** instead of the pitch steppers. Choose **Pulse**, **Triangle**, or **Noise**, and the note keys then play the instrument on that sound generator.

## Exporting

You export a reconstruction from the **Reconstruction** menu:

- **Export instruments ▸ FamiTracker instruments...** writes one `.fti` file per channel.
- **Export instruments ▸ Bitphase presets...** writes the same instruments as `.json`.
- **Export instruments ▸ NSF program...** writes a single `.nsf` file that plays the whole reconstruction on a NES.
- **Export to WAV...** renders the audio using the channel and stem checkboxes you have set.

**Export instrument...** in the **Instruments** panel writes only the channel you are looking at, in whichever format you choose in the save dialog. See [where your files live](files.md#exported-files).

To use a reconstruction in a song, right-click it and choose **Add to Sequencer**.
