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

Click the waveform to play from that point. While playback is paused, a click moves the playback position. Drag the waveform to move the view, and double-click to fit the view.

## Hearing what each recording contributed

The **Stems** card lists the recordings used to build a reconstruction. It groups them by the level each one was given. Every row has a checkbox for each channel that the recording used, and the checkbox at the front toggles all of them.

A colored square at the left of each row is the color that recording is drawn in under the waveform, so you can tell which bars came from which recording.

Double-click a row to show that recording in your file browser.

Under the waveform is a row of colored bars, one line per channel. A letter at the left of each line names its channel: **P** for Pulse 1, **p** for Pulse 2, **T** for Triangle and **N** for Noise. Each bar shows which recording played that stretch, in the recording's own color; a dark stretch means nothing was played there. A recording you have unchecked keeps its color there, drawn faint, so you can still see which recording held a stretch while you listen without it. The bars appear when a reconstruction was built from more than one recording.

Uncheck a channel to silence it in the waveform, in playback, in the original audio and in a WAV export. The **Instruments** panel follows too: it shows the envelopes of the part you are listening to, and the sizes it states measure that part. Uncheck every recording on a channel and the channel reads as empty. This lets you see and hear what one recording added, channel by channel. The saved reconstruction keeps every channel, whatever you uncheck.

The checkboxes also decide what an instrument edit changes. A frame belongs to the recording that played it, so an edit changes the frames of the recordings you have checked and leaves the rest alone. Uncheck a recording to shape one part of a channel without touching the others.

Notes you write into silence belong to no recording. They gather in an **Edits** row below the recordings, with checkboxes of its own, and removing a recording leaves them alone.

**Collapse levels** shows the whole list as one table.

**x** at the end of a row removes that recording from the reconstruction. The app asks you to confirm first. The recording goes silent, its row disappears, and the change is saved when you save the reconstruction. A reconstruction needs at least one recording, so the **x** of the last row is disabled. The **Edits** row has no **x**, because it names no recording.

## Editing instruments

The **Instruments** panel shows what each channel plays. A band beneath each set of bars carries the same colors as the bars under the waveform, so you can see which recording each frame came from while you edit it. You edit the sequences by dragging the bars or typing values.

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

Every export writes what you see and hear: the instrument files hold the same part of each channel that the **Instruments** panel draws.

**Export instrument...** in the **Instruments** panel writes only the channel you are looking at, in whichever format you choose in the save dialog. See [where your files live](files.md#naming-exported-files).

To use a reconstruction in a song, right-click it and choose **Add to Sequencer**.
