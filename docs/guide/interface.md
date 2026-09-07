# The interface

_SampleToNES_ is one window: a menu bar at the top, four tabs, and a status bar
at the bottom. Each tab works left to right — pick something on the left, set it
up in the center, refine it on the right.

This page covers the **Main**, **Instructions**, and **Reconstructions** tabs
and the menus around them. The **Sequencer** has [its own page](sequencer.md).

## Main

The **Main** tab turns an audio file into a
[reconstruction](../concepts/reconstruction.md). Most sessions start here.

Pick an audio file — or a whole folder — in the **Filesystem** browser on the
left, set up the conversion in the center, and click the button, which names the
run it is about to make: **Convert bass**, **Convert 6 recordings**, **Mix 5
recordings**. The browser reopens the folders you were last working in, and
**Collapse all** folds them away again. The [instruction
library](../concepts/instruction-library.md) your settings need is built the
first time you convert, so you can start straight away.

**Destination:** at the foot of the card names where a run writes — the document
a single conversion makes, or the folder a longer run fills — and while a run
goes on an **Input:** line above it names the recording being read. Click either
path to open it in your file manager. Afterwards, **Load** opens
the new reconstruction on the **Reconstructions** tab — after a folder run the
button reads **Open** instead. **Cancel** stops a run, and only one runs at a
time.

A recording you added by name is written every time you convert, so where a
reconstruction of that name already stands the app asks first — naming the one it
is about to replace, or counting them where a run would replace several — and
**Convert anyway** goes ahead. Recordings that came in with a folder are left
where their reconstruction already stands, so rerunning a folder carries on from
where you stopped.

### What to convert

The card holds a list of what a run converts. Double-click a recording in the
browser to add it; right-click and choose **Add as stem**, or Ctrl-click, to do
the same. A plain click plays the recording, so you can listen through a folder
before you take anything from it. Ctrl-click a folder — or use **Add folder** —
and the folder joins as one row standing for every recording below it, however
deep the tree goes. Reading a large tree takes a moment, so a window names the
folder and counts what it has found, with a **Stop** if you picked the wrong one.

The channels are named once above the rows, and each row shows one recording and
a checkbox under every channel it may use. Untick them all and the row grays out:
that recording sits out of the conversion, and stays in the list so you can bring
it back. **x** takes a row out; taking out a folder takes everything it holds.
The list grows with what you gather and scrolls once it fills the card, so the
cards below it stay where you left them.

A folder's row names how many recordings it brought in, and its checkboxes read
all three ways: ticked where every recording in it uses that channel, filled in
that channel's own color where they differ, and empty where none does. One click
settles the whole folder.

A folder arrives closed. Click the marker beside its name — or double-click the
name, or use **Show the recordings** in its menu — and it opens onto the
recordings it holds, in a panel of its own that scrolls once there are more than
it can show. Each of those recordings has its own checkboxes, so you can answer
for one of them without breaking the folder up. Double-clicking a recording plays
it.

### One reconstruction each, or one from them all

**Output**, at the head of the card, names what the run writes. On **One per
recording**, every recording in the list gets a reconstruction of its own, and
the ones a folder holds are written into a tree mirroring that folder. On **One
from all**, they mix into a single reconstruction instead.

A mix reaches eight recordings, so choosing it with a longer list asks which ones
to mix, and so does adding a folder that overflows what is left. The question
shows the same rows the card does — folders open onto what they hold, and one
click answers for a whole folder, its box filling where only some of what it
holds is picked. Adding a folder stands the recordings the mix is already built
from beside the ones the folder offers, so letting one go is how you make room
for another. As many as a mix holds arrive ticked, the line above counts what you
have picked, and **Add** settles the mix once the pick fits.

From the second recording of a mix, rows sit in **level** bands. A level is a turn
to choose: every recording on level 1 picks its channels before any on level 2, so
a lead can take what it needs before a pad does. Drag a row onto another row to join that row's
level, or into the gap between two levels to give it a level of its own.
Right-clicking a row lists the same moves as menu items, alongside the
recording's own actions — copy its name or path, or show the file in your file
manager. **Order** sets how the levels take turns: round by round, or one level
filled before the next picks.

**Channels per source**, below the list, caps how many channels one recording may
hold in a single frame, and it applies to every conversion. Set to 1, each
recording gets a single voice. It stands beside **Order** once there is a list to
answer for. The output switch, the cap and the order are remembered, so the app
opens on the run you last set up.

Reconstructing a file or a folder from the browser converts that one thing, so it
asks first where you have already gathered a list.

### Settings

A few settings are worth knowing before you convert. **Drive** sets how hard the
channels are pushed and holds for the whole run, so it stands at the top of
**Source settings** whatever you are looking at. Below it the card names
the row you clicked in the converter's list — a folder reads how many recordings
it stands for — and gives that row a box under every channel: one for the channel
it takes, and one for the bend on it. A folder whose recordings differ on a
channel fills that box in the channel's own color and leaves it unticked, until
one click settles them all. Press a channel's key to set that channel across
everything listed at once. **General settings** holds the analysis options:
sample rate, NES frequency, generation method, and feature scaling. The rest,
including the worker count and the output and library folders, sit under
**Advanced settings**, which **View ▸ Show advanced settings** reveals.
[Configuration](configuration.md) explains each one.

## Reconstructions

The **Reconstructions** tab is where you compare a reconstruction with the
original, fine-tune it, and export it.

Open a saved reconstruction from the **Browser** on the left. It shows the same
files two ways: **By configuration** groups them by the settings they were made
with, and **By sample** gathers every version of one source audio together. If
the reconstruction you have open has unsaved edits, you are asked whether to
save it first. Play it back and switch **Play audio source:** between
**Reconstruction** and **Original audio** to compare the two. **Locate original
audio** re-links the source files if they have moved.

### Finding your way around the browser

To keep the reconstructions you return to within reach, right-click one — or a
whole folder — and choose **Mark as favorite**, which highlights it in both
views. Tick **Favorites only** under the search box to narrow the browser to
your favorites and everything inside them.

Narrowing keeps whatever folders you had open, so ticking the box on and off
leaves the tree as you left it. To have the browser open its way down to each
favorite instead, turn on **View ▸ Auto-expand favorites**, which you can set
for reconstructions and for folders separately. It expands each time you tick
**Favorites only**, and unticking folds those rows back.

**Collapse all**, beside the refresh button, folds the whole tree in one click.
Whatever you leave open is remembered for the next time you start the app.

### The Stems card

A reconstruction mixed from several recordings has a **Stems** card. It lists
each recording under the level it was picked on — the same list the converter
showed you while you were gathering.

Each row has a colored box for every channel that recording actually took, and
a box at the front that moves all of them at once. Untick one and those frames
go silent everywhere: in the waveform, in playback, in the original audio, and
in a WAV export. That is how you hear what each recording contributed, channel
by channel. A channel you have switched off under the waveform shows its column
grayed, and your ticks stay where you put them.

Click a row to show its recording in your file browser, and tick **Collapse
levels** to read the whole list as one table. These ticks last for the session:
saving records which recording owns which frame, not what you were listening to.

**x** at the end of a row removes the recording from the reconstruction for
good, so the app asks first. Its frames go silent and its row disappears, and
the rest play as they did. One recording always stays, so the last row's **x**
is grayed out.

### Exporting

To get your results out, use the **Reconstruction** menu. **Export instruments ▸
FamiTracker instruments...** writes one `.fti` per channel, **Bitphase
presets...** writes the same as `.json`, **NSF program...** writes a single
`.nsf` that plays the whole reconstruction on a NES, and **Export to WAV...**
renders the audio. To use the reconstruction in a song, right-click it and
choose **Add to Sequencer** (see the [sequencer guide](sequencer.md)).

### Editing instruments

For finer control, the **Instruments** panel on the right shows each channel's
instrument — its pitch, volume, arpeggio, and duty sequences — which you can
edit by dragging the bars or typing values. Typing `|` before an item marks where
that sequence repeats from while a note is held, so `15 14 | 12 10` attacks and then
circles the last two values. Each sequence keeps its own point, so a short duty cycle
can circle beside a longer volume envelope. Clearing a sequence hands that dimension
back to the channel, so an instrument with its volume sequence cleared plays at
whatever volume the channel is set to.

Beside each channel is the room its instrument takes on the NES, with the whole
sample's above them, so you can see what an edit costs. The figures are in bytes
and count what a FamiTracker export saves, so clearing a sequence brings them
down. **Export instrument...** writes the channel you are looking at, in
whichever tracker format you pick in the save dialog — see [where your files
live](files.md#exported-files).

An **instrument** — a voice you wrote by hand rather than converted, see the
[sequencer guide](sequencer.md#voices-samples-and-instruments) — opens here too, from
the **Voices** list's right-click ▸ **Edit**. It stands on no recording, so the tab
shows its envelopes alone: one set every channel reads, under the instrument's own
name. A row of the tracker states the note it sounds at, so the pitch steppers stand
down and **Audition** takes their place: pick **Pulse**, **Triangle** or **Noise**, and
the note keys — `Z` to `M` for one octave and `Q` to `U` for the one above it, at the
octave the tracker types in — play the instrument on that generator. The waveform card
draws what you would hear, in that generator's own color, and redraws as you edit.
Editing an instrument puts away whatever reconstruction the tab held.

## Instructions

The **Instructions** tab builds and browses the [instruction
library](../concepts/instruction-library.md) for your current settings, and lets
you inspect single instructions.

You will rarely come here just to build a library — converting on the **Main**
or **Reconstructions** tab builds the matching one for you. It is useful for
building one ahead of time, or for exploring what a configuration can produce:
pick an instruction and its waveform and spectrum appear with a player, so you
can hear a single NES tone on its own.

**Generate library** builds the library for the current settings; if one already
exists, _SampleToNES_ asks **Regenerate library?** first. **Cancel generation**
stops it, **Refresh instructions data** re-reads the catalog, and selecting an
entry in the **Libraries** tree loads it.

## Around the app

The menu bar and status bar sit outside the tabs.

Each menu covers one kind of work: **File** for projects, **Edit** for undo,
redo, and whatever your cursor is on, **Reconstruction** for the current
reconstruction and its exports, **Voice** for the ways a voice comes into the
sequencer and what the one you picked offers, **Playback** for playing and for
muting the sequencer's channels, **View** for settings and the window, and **Help**
for **About**. What **Edit** offers below undo and redo follows your cursor: the
block actions of the sequencer grid you are in, or the actions of the voice you
have picked in the **Voices** list.

**Voice** answers "how do I get a voice in" on its own: **New instrument**, **Add
sample from file...**, **Import instrument...**, and **Add to Sequencer** stand
together at the top, and the actions of the voice you picked follow — the same set the
list's own right-click menu prints. See [voices](sequencer.md#voices-samples-and-instruments).

Two items write audio you can play anywhere: **Reconstruction ▸ Export to
WAV...** for the reconstruction you have open, and **File ▸ Render song...**
(`Ctrl+Shift+E`) for the sequencer's whole song, as a WAV or an MP3 — [rendering
to audio](sequencer.md#rendering-to-audio) covers its options.

Two other items are easy to miss. **View ▸ Show advanced settings** reveals the
extra options on the **Main** tab. **Playback ▸ Audio settings...** picks the
playback device, sample rate, and buffer size; these change what you hear, while
the **Sample rate** and **NES frequency** on the **Main** tab change how audio
is reconstructed.

`F1` to `F4` switch tabs in order — **Main**, **Reconstructions**,
**Sequencer**, and **Instructions**. They work while you are typing, so any tab
is one key away.

`1` to `4` toggle the four NES channels on the tab in front of you: the channels
that take part on **Main**, the channels drawn on **Reconstructions**, and the
song's mix anywhere else. In the sequencer's grids the digits type values into
the cell you are on, so mute there with the channel names or the **Playback ▸
Channels** menu.

### Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists everything you can do from the
keyboard and lets you change any of it. Click an action's shortcut and press the
keys you want, or type them into the box below the list. If another action
already uses those keys, the app tells you which one and asks whether to hand
them over. **Reset to defaults** puts everything back, and your changes take
effect when you press **OK**.

On macOS the shortcuts use Command where other platforms use Control. What you
change is saved with your settings and is there the next time you start.

Project properties belong to a project and are covered in the [sequencer
guide](sequencer.md).
