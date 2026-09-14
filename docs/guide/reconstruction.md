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

The **Source** card switches playback between **Reconstruction** and **Original audio**, so you can compare the two. The **Waveform** card has a checkbox for each channel. Keys `1` to `4` switch the same checkboxes.

## Hearing what each recording contributed

The **Stems** card lists the recordings used to build a reconstruction. It groups them by the level each one was given. Every row has a checkbox for each channel that the recording used, and the checkbox at the front toggles all of them.

Uncheck a channel to silence it in the waveform, in playback, in the original audio and in a WAV export. This lets you hear what one recording added, channel by channel. The saved reconstruction keeps every channel, whatever you uncheck.

**Collapse levels** shows the whole list as one table.

**x** at the end of a row removes that recording from the reconstruction. The app asks you to confirm first. The recording goes silent, its row disappears, and the change is saved when you save the reconstruction. A reconstruction needs at least one recording, so the **x** of the last row is disabled.

## Editing instruments

The **Instruments** panel shows what each channel plays. You edit the sequences by dragging the bars or typing values.

Each channel has its own set of sequences:

- **Pulse 1** and **Pulse 2** — volume, arpeggio, pitch, hi-pitch, and duty cycle.
- **Triangle** — volume, arpeggio, pitch, and hi-pitch.
- **Noise** — volume, arpeggio, and duty cycle.

Type `|` before a value to mark where the sequence repeats while a note is held. `15 14 | 12 10` plays the attack once and then loops the last two values.

Clear a sequence to use the channel's own setting. For example, an instrument with an empty volume sequence plays at the volume the channel is set to. Each channel shows how many bytes its instrument takes on the NES, so you can see how much space an edit uses.

You can also edit an **instrument** here, a voice you write by hand. The [sequencer guide](sequencer.md#voices-samples-and-instruments) describes instruments. Right-click one in the **Voices** list and choose **Edit**.

For an instrument, the panel shows **Audition** in place of the pitch steppers. Choose **Pulse**, **Triangle** or **Noise**, and the note keys play the instrument on that sound generator.

## Exporting

You export a reconstruction from the **Reconstruction** menu:

- **Export instruments ▸ FamiTracker instruments...** writes one `.fti` file per channel.
- **Export instruments ▸ Bitphase presets...** writes the same instruments as `.json`.
- **Export instruments ▸ NSF program...** opens the **Export NSF program** window and writes a single `.nsf` file that plays the whole reconstruction on a NES. The window works as it does [in the sequencer](sequencer.md#exporting-an-nsf-program). A reconstruction has no order frames, so **Repeat** has no **From a frame**. It has no samples either, so **Level** has no **Samples**. You can only select the channels the reconstruction uses.
- **Export to WAV...** renders the audio using the channel and stem checkboxes you have set.

**Export instrument...** in the **Instruments** panel writes only the channel you are looking at, in whichever format you choose in the save dialog. See [where your files live](files.md#naming-exported-files).

To use a reconstruction in a song, right-click it and choose **Add to Sequencer**.
