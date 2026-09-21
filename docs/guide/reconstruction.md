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
[level](converting.md#one-reconstruction-each-or-one-mix-from-all) each one was given. Every row has a
checkbox for each channel the recording used, and the checkbox at the front switches all of them.

A colored square at the left of each row is the color that recording is drawn in under the waveform.
Double-click a row to show the recording in your file browser.

Under the waveform is a row of colored bars, one line per channel, with a letter naming the channel:
**P** for Pulse 1, **p** for Pulse 2, **T** for Triangle and **N** for Noise. Each bar shows which
recording played that stretch, in that recording's color, and a dark stretch means nothing was played
there. A recording you have unchecked keeps its color, drawn faint, so you can still see which
recording held a stretch while you listen without it. The bars appear when there is more than one
thing to tell apart: a reconstruction built from
several recordings, or one built from a single recording that you have since edited by hand. Your own
edits are drawn in a color of their own.

Uncheck a channel to silence it in the waveform, in playback, in the original audio and in a WAV
export. Uncheck every recording on a channel and the channel reads as empty. This lets you hear what
one recording added, channel by channel. The saved reconstruction keeps every channel, whatever you
uncheck.

The **Instruments** panel follows the same checkboxes: it shows the sequences of the part you are
listening to, and the sizes it states measure that part. So the checkboxes also decide what an edit
changes. A frame belongs to the recording that played it, so an edit reaches the frames of the
recordings you have checked and leaves the rest alone — uncheck a recording to shape one part of a
channel without touching the others.

Notes you write into silence belong to no recording. They gather in an **Edits** row below the
recordings, with checkboxes of its own, and removing a recording leaves them alone.

**Collapse levels** shows the whole list as one table.

**x** at the end of a row removes that recording from the reconstruction, after asking you to confirm.
The recording goes silent, its row disappears, and the change is saved when you save the
reconstruction. A reconstruction needs at least one recording, so the **x** of the last row is
disabled. The **Edits** row has no **x**, because it names no recording.

## Editing instruments

The **Instruments** panel shows what each channel plays, as one
[sequence](../glossary.md#sequence-envelope) per dimension. A band beneath each set of bars carries the
same colors as the bars under the waveform, so you can see which recording a frame came from while you
edit it. Edit a sequence by dragging its bars or typing values.

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

You can edit an [**instrument**](../glossary.md#instrument) here as well — a voice you write by hand,
which the [sequencer guide](sequencer.md#voices-samples-and-instruments) describes. Right-click one in
the **Voices** list and choose **Edit**.

For an instrument, the panel shows **Audition** in place of the pitch steppers. Choose **Pulse**,
**Triangle** or **Noise**, and the note keys play the instrument on that channel.

## Exporting

You export a reconstruction from the **Reconstruction** menu:

- **Export instruments ▸ FamiTracker instruments...** writes one `.fti` file per channel.
- **Export instruments ▸ Bitphase presets...** writes the same instruments as `.json`.
- **Export instruments ▸ NSF program...** opens the **Export NSF program** window and writes a single
  `.nsf` file that plays the whole reconstruction on a NES. The window works as it does [in the
  sequencer](sequencer.md#exporting-the-song), with two differences: a reconstruction has no order
  frames, so **Repeat** has no **From a frame**, and it has no samples either, so **Level** has no
  **Samples**. You can select only the channels the reconstruction uses.
- **Export to WAV...** renders the audio using the channel and recording checkboxes you have set.

Every export writes what you see and hear: the instrument files hold the same part of each channel
that the **Instruments** panel draws.

**Export instrument...** in the **Instruments** panel writes only the channel you are looking at, in
whichever format you choose in the save dialog. See [where your files
live](files.md#naming-exported-files).

To use a reconstruction in a song, right-click it and choose **Add to Sequencer**.
