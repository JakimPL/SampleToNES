# The interface

_SampleToNES_ has four tabs, and `F1` to `F4` switch between them:

- **Main** (`F1`) — turn audio files into [reconstructions](../concepts/reconstruction.md).
- **Reconstruction** (`F2`) — listen to a reconstruction, edit its instruments, and export it.
- **Sequencer** (`F3`) — arrange reconstructions into a song. It has [its own page](sequencer.md).
- **Instructions** (`F4`) — build and browse the [instruction
  library](../concepts/instruction-library.md) a conversion draws from.

Work moves through them in that order. You convert on **Main**, and when the run
finishes **Load** opens the result on **Reconstruction**. From there **Add to
Sequencer** hands it to a song. The **Instructions** tab is optional: converting
builds the library your settings need, so you come here only to build one ahead
of time or to look at what one holds.

Two things sit outside the tabs. Everything a reconstruction exports to is on the
**Reconstruction** menu rather than on a tab. And the **Edit** and **Voice**
menus rebuild themselves around whatever your cursor is on, so what they offer
depends on where you are working.

## Choosing what to convert

The **Converter** card on the **Main** tab holds a list of what a run converts.
Fill it from the **Filesystem** browser:

- Double-click an audio file, or Ctrl-click it, to add it. Right-click ▸ **Add as
  stem** does the same.
- Ctrl-click a folder, or right-click ▸ **Add folder**, to add every recording
  below it, however deep the tree goes.

Reading a large folder takes a moment, so **Reading the folder** appears while
the scan runs, counting what it has found, with a **Stop** if you picked the
wrong one. A folder holding no audio says so instead of joining the list.

A single click plays a recording while **Playback ▸ Autoplay** (`Ctrl+P`) is on,
so you can listen through a folder before taking anything from it. With Autoplay
off, use right-click ▸ **Play**.

**x** takes a row out of the list, and taking out a folder takes everything it
holds.

## Choosing which channels a recording uses

The NES has four sound channels — **Pulse 1**, **Pulse 2**, **Triangle**, and
**Noise** — and every recording in the list carries a checkbox under each of
them. Tick the ones that recording may use. Untick them all and the row grays
out: it stays in the list and sits out of the conversion, so you can bring it
back. Pressing `1` to `4` switches one channel across every recording at once.

A folder is a single row standing for the recordings below it, so its checkboxes
read three ways: ticked where every recording in it uses that channel, filled in
the channel's own color where they differ, and empty where none does. One click
settles the whole folder. To answer for one recording on its own, open the folder
— click the marker beside its name, or double-click the name.

**Source settings** holds two more things. **Drive** sets how hard the channels
are pushed and applies to the whole run. Below it, the card names the row you
clicked in the list and gives it a box per channel, with a **bend** box beside it
on **Pulse 1**, **Pulse 2**, and **Triangle** that tunes each note to the
recording's exact pitch. Noise takes no bend.

**Channels per source** caps how many channels one recording may hold in a single
frame, from 1 to 4. Set it to 1 and each recording gets a single voice.

## One reconstruction each, or one mix from all

**Output**, at the head of the **Converter** card, decides what the run writes.

- **One per recording** gives every recording in the list a reconstruction of its
  own. The ones that came in with a folder are written into a tree mirroring that
  folder.
- **One from all** mixes them into a single reconstruction. Folders are flattened
  into the recordings they hold.

A mix holds up to eight recordings. Switching to **One from all** with more than
that listed asks which to mix, and so does adding a folder that overflows the
room left. The question lists the same rows the card does, counts what you have
picked, and **Add** settles it once the pick fits. Adding one more recording to a
mix that is already full does nothing, so let one go first.

From the second recording of a mix, rows sit in **level** bands. A level is a
turn to choose: everything on level 1 picks its channels before anything on level
2, so a lead can take what it needs before a pad does. Drag a row onto another to
share its level, or into a gap to give it a level of its own; right-clicking a
row lists the same moves. **Order** decides how the levels take turns — **Round
robin** gives every level a turn each round, **Strict** fills one level before the
next picks.

## Running a conversion

Click the button under **Output** to start. It names what it is about to do, and
only one conversion runs at a time; while one does, the button reads **Cancel**.

**Destination:** says where the run writes — the document a single conversion
makes, or the folder a longer run fills. Click the path to open it in your file
manager. If converting would replace a reconstruction that already exists, the
app asks first.

When the run finishes, **Load** opens the result on the **Reconstruction** tab;
after a run of several, the button reads **Open** instead. The first conversion
with a given set of settings builds the [instruction
library](../concepts/instruction-library.md) it needs, which takes a while; later
runs on the same settings reuse it.

## Listening to a reconstruction

Open a saved reconstruction from the **Browser** on the **Reconstruction** tab.
It groups them two ways in one tree: **By configuration**, by the settings they
were made with, and **By sample**, gathering every version of one source audio
together. If what you have open has unsaved edits, you are asked whether to save
it first.

To keep the ones you return to within reach, right-click a reconstruction — or a
whole folder — and choose **Mark as favorite**, then tick **Favorites only** to
narrow the tree to them.

The **Source** card switches playback between **Reconstruction** and **Original
audio**, so you can hear the two against each other. The **Waveform** card draws
the channels with a checkbox for each; `1` to `4` flip the same boxes.

## Hearing what each recording contributed

The **Stems** card lists the recordings a reconstruction was built from, under
the level each was picked on. Every row carries a box for each channel that
recording took, and a box at the front that moves all of them together.

Untick one and those frames fall silent everywhere — in the waveform, in
playback, in the original audio, and in a WAV export — which is how you hear what
one recording contributed, channel by channel. These boxes are listening state
only and change nothing that is saved. **Collapse levels** reads the whole list
as one table.

**x** at the end of a row removes that recording from the reconstruction and asks
first: its frames fall silent and its row disappears, and the change is written
only when you save. One recording always stays, so the last row's **x** is
disabled.

## Editing instruments

The **Instruments** panel shows what each channel plays, as sequences you edit by
dragging the bars or typing values. Which sequences a channel has depends on the
channel: **Pulse 1** and **Pulse 2** carry volume, arpeggio, pitch, hi-pitch, and
duty cycle; **Triangle** the same without duty cycle; **Noise** carries volume,
arpeggio, and duty cycle.

Typing `|` before a value marks where that sequence repeats from while a note is
held, so `15 14 | 12 10` attacks and then circles the last two. Clearing a
sequence hands that dimension back to the channel, so an instrument with its
volume cleared plays at whatever volume the channel is set to. Each channel
states how many bytes its instrument takes on the NES, so you can see what an
edit costs.

A hand-written **instrument** — a voice with no recording behind it, see the
[sequencer guide](sequencer.md#voices-samples-and-instruments) — opens here too,
from the **Voices** list's right-click ▸ **Edit**. It stands on no recording, so
**Audition** takes the place of the pitch steppers: pick **Pulse**, **Triangle**,
or **Noise** and the note keys play the instrument on that generator.

## Exporting

Everything a reconstruction exports to is on the **Reconstruction** menu.
**Export instruments ▸ FamiTracker instruments...** writes one `.fti` per
channel, **Bitphase presets...** writes the same as `.json`, and **NSF
program...** writes a single `.nsf` that plays the whole reconstruction on a NES.
**Export to WAV...** renders the audio, honoring the channel and stem boxes you
have set.

**Export instrument...** in the **Instruments** panel writes the one channel you
are looking at, in whichever format the save dialog is set to. See [where your
files live](files.md#exported-files).

To use a reconstruction in a song, right-click it and choose **Add to
Sequencer**.

## The instruction library

The **Instructions** tab builds and browses the [instruction
library](../concepts/instruction-library.md), the catalog of NES tones a
conversion searches. Converting builds the one your settings need, so you rarely
need to come here.

It is useful for building a library ahead of a long session, and for exploring
what a configuration can produce: pick an instruction and its **Waveform** and
**Spectrum** appear, so you can see and hear a single NES tone on its own.
**Generate library** builds one for your current settings, and reads
**Regenerate instructions** once a library is loaded.

## The menus

Each menu covers one kind of work:

- **File** — projects, the module and program a song exports to, and rendering a
  song to audio.
- **Edit** — undo and redo, then the actions of whatever your cursor is on.
- **Reconstruction** — making, opening and saving reconstructions, and every
  export of one.
- **Voice** — the ways a voice comes into the sequencer, and the actions of the
  one you picked.
- **Playback** — playing, autoplay, following the song, and muting channels.
- **View** — advanced settings, favorites, the display, and the shortcuts.
- **Help** — **About**.

Two items are easy to miss. **View ▸ Show advanced settings** reveals **Advanced
settings** on the **Main** tab, which holds the generation method, the feature
scaling, the worker count, and the library and output folders.
[Configuration](configuration.md) explains each one. **Playback ▸ Audio
settings...** picks the device, sample rate, and buffer size you listen through,
which are separate from the **Sample rate** and **NES frequency** on the **Main**
tab that decide how audio is reconstructed.

Project properties belong to a project and are covered in the [sequencer
guide](sequencer.md).

## Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists everything you can do from the
keyboard and lets you change any of it. Click an action's shortcut and press the
keys you want. If another action already holds them, the app names it and asks
whether to hand them over. **Reset to defaults** puts everything back, and your
changes take effect when you press **OK**.

`Space` plays and pauses and `Esc` stops, wherever you are. On macOS the
shortcuts use Command where other platforms use Control. What you change is saved
with your settings and is there the next time you start.
