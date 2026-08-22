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
sample** (or **Convert directory** for a folder). The browser opens the folders you
were last working in, and **Collapse all** folds them away again. The
[instruction library](../concepts/instruction-library.md) for your settings is
built automatically the first time it is needed, so you can convert straight away.
While it runs, the panel names the file going in and where the result is going, and
clicking either path shows it in your file manager. When a run writes one
reconstruction, **Load** opens it on the **Reconstructions** tab; a whole folder of
them offers **Open** instead. **Cancel** stops a run, and only one runs at a time.

**Stems mode** turns the card into a list of the recordings mixed into one
reconstruction. Tick it and click each recording in the browser, or right-click one
and choose **Add as stem** — that starts a stems conversion from a classic one in a
single step. **Add folder as stems** offers everything in a folder, as does
Ctrl-clicking it while you are gathering; where a folder holds more recordings than
the list has room for, you pick which ones.

Each row names its recording and carries a checkbox per channel that recording may
use. Untick them all and the row greys out: that recording takes no part in the
conversion, and its row stays listed so you can bring it back.

The rows sit under **level** bands, and a level is a turn to choose: every recording
on level 1 picks its channels before any on level 2, so a lead can take what it needs
before a pad does. Drag a row by its handle onto another row to share that row's
level, or onto the gap between two levels to give it a level of its own.
Right-clicking a row names the same moves in words, alongside the recording's own actions — its name or path to the clipboard, and the file shown in your file manager. **Order** decides how the levels
take turns — round by round, or one level filled before the next picks — and **x**
takes a row out. Untick **Stems mode** and the first recording stays as your single
selection.

**Channels per source** caps how many channels one recording may hold in a single
frame, and it applies to every conversion — one file, a whole folder, or a stems
mix. Leaving it at one channel per source gives each recording a single voice.

Reconstructing a file or a folder from the browser converts that one thing, so while
you are gathering stems it asks before dropping the list.

A few settings are worth knowing before you convert. Under **Reconstructor
settings**, the **Channels** toggles choose which channels take part — at least
one must be on — and **Drive** sets how hard they are pushed. **General settings**
holds the analysis options: sample rate, NES frequency, generation method, and
feature scaling. The rest, including the worker count and the output and library
folders, sit under **Advanced settings**, which **View ▸ Show advanced settings**
reveals. [Configuration](configuration.md) explains each one.

## Reconstructions

The **Reconstructions** tab is where you audition a reconstruction against the
original, fine-tune it, and export it.

Open a saved reconstruction from the **Browser** on the left, which offers the
same files two ways: **By configuration** groups them by the settings they were
made with, and **By sample** gathers every version of one source audio together.
If the current reconstruction has unsaved edits, you are asked whether to save it
first. You can play it back and
switch **Play audio source:** between **Reconstruction** and **Original audio** to
compare the two, and **Locate original audio** re-links the source file if it has
moved.

To keep the reconstructions you return to within reach, right-click one — or a
whole folder — and choose **Mark as favorite**, which highlights it in both views.
Tick **Favorites only** under the search box to narrow the browser to your
favorites and everything inside them. The browser keeps the folders you had open
while it narrows, so switching the tick on and off leaves the tree as you left it.
If you would rather it opened its way down to each favorite for you, turn that on
under **View ▸ Auto-expand favorites**, which answers for reconstructions and for
folders separately. It opens the way down each time you tick **Favorites only**,
and unticking folds those rows back.

**Collapse all**, beside the refresh button, folds the whole tree away in one
click. Whatever you leave open is remembered, so the tree comes back the way you
left it the next time you start the application.

A reconstruction mixed from several recordings carries a **Stems** card listing
each of them with the channels it took. Untick one and its frames fall silent
everywhere at once — in the waveform, in playback, in the original audio, and in a
WAV export — so you can hear what each recording contributed. The ticks are yours
for the session; saving records the assignment, never the selection.

To get your results out, use the **Reconstruction** menu. **Export instruments ▸
FamiTracker instruments...** writes one `.fti` per channel, **Bitphase
presets...** writes the same as `.json`, **NSF program...** writes a single `.nsf`
that plays the whole reconstruction on a NES, and **Export to WAV...** renders the
audio. To use the reconstruction in a song, right-click it and choose **Add to
Sequencer** (see the [sequencer guide](sequencer.md)).

For finer control, the **Instruments** panel on the right shows each channel's
instrument — its pitch, volume, arpeggio, and duty sequences — which you can edit
by dragging the bars or typing values. Clearing a sequence hands that dimension to
the channel, so an instrument with no volume sequence plays at whatever level its
channel carries. Beside each channel is the room its instrument takes on the NES,
with the whole sample's above them, so you can see what an edit costs. The figures
are in bytes, and they count what a FamiTracker export saves, so clearing a
sequence brings them down. **Export instrument...** writes the channel on show, for
whichever tracker the save dialog's file type names — see [where your files
live](files.md#exported-files).

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
**About**. What **Edit** offers below undo and redo follows your cursor: the block
actions of the sequencer grid you are in, or the actions of the sample you have
picked in the **Samples** list.

Two items write audio you can play anywhere: **Reconstruction ▸ Export to WAV...**
for the reconstruction on show, and **File ▸ Render song...** (`Ctrl+Shift+E`) for
the sequencer's whole song, as a WAV or an MP3 —
[rendering to audio](sequencer.md#rendering-to-audio) covers the options it offers.

Two other items are easy to miss. **View ▸ Show advanced settings** reveals the extra
options on the **Main** tab. **Playback ▸ Audio settings...** picks the playback
device, sample rate, and buffer size; these change what you hear, while the
**Sample rate** and **NES frequency** on the **Main** tab change how audio is
reconstructed.

`F1` to `F4` bring up the four tabs in order — **Main**, **Reconstruction**,
**Sequencer**, and **Instructions** — and work while you are typing, so any tab is
one key away.

`1` to `4` toggle the four NES channels on the tab in front of you: the
the channels on **Main**, the channels drawn on **Reconstructions**, and the song's
mix on the **Sequencer**. In the sequencer's grids the digits type values into the
cell you are on, so use the channel names or the **Playback ▸ Channels** menu to
mute there.

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
