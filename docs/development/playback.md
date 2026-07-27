# Playback and Transport

This document governs sound across the application: what may be heard, who decides, and what each
transport command means. Consult it when adding audio a user can start, a surface that starts it, or
a control over what is heard. The contracts here bind every tab and every player. It complements
`docs/development/architecture.md` (which owns the keyboard-routing layer, §12) and
`docs/development/guidelines.md`.

---

## Principles

1. **The output is one scarce resource, arbitrated by intent.** There is a single device, a single
   stream, and a single thing sounding. Audio a user asked a tab to play outranks audio a click
   auditioned, so every request states which kind it is and the arbiter — not the caller's
   eagerness — decides what is heard.
2. **Ownership is the state.** Which source owns the live stream is the one fact that answers "what
   is playing": commands, labels, and indicators all derive what they do and show from it, so they
   agree by construction.
3. **A command addresses one target, resolved from where the user is.** Context decides which source
   a verb means, and one resolution serves every verb, so the same key means the same thing on a
   given screen every time.
4. **Surfaces describe the target; the transport decides.** The menu, the toolbar, and the keyboard
   reach identical verbs and report identical state, so a new surface adds another way in to the
   same behaviour.
5. **Listening choices stay out of the document.** What the user chooses to hear is session state;
   what the project holds is the whole song. Saving, export, rendering, and history read the
   document, so each of them works on the full song whatever the user is listening to.
6. **Live state is pulled while sound is produced.** A player reads the settings that shape its
   sound as it renders, so a change is heard as the render-ahead buffer drains. This is what lets a
   listening control take effect inside the sound already playing.

## Two kinds of sound

**Preview** — a quick audition fired by a click: a file or reconstruction in a browser tree, a
sample in the sequencer. A preview is ephemeral. It sounds once, holds the device without claiming
ownership of it, and is meant to be heard and forgotten. It yields the device to intentional
playback, and it answers to Stop.

**Intentional playback** — the audio a tab is built around: a reconstruction's audio, an
instruction's audio, or the sequencer song. It is owned by the source that started it, and it is
resumable, seekable, and stoppable. One intentional source at most is engaged at any moment.

Priority ranks the two kinds and settles every contest for the device: starting intentional playback
preempts a sounding preview, and a preview requested while intentional playback holds the device is
declined.

## Engagement

A source is **engaged** while it owns the device output, whether it is sounding or held paused. A
source therefore reports itself engaged only while *its own* audio is the one on the device; while a
preview sounds, ownership rests outside every source and each of them reports itself idle.

Engagement is the ownership test of principle 2 in practice, and it is the single fact the transport
and the toolbar consult.

## The target

The transport acts on one **target**, resolved in two steps: the active tab's own source when that
tab has one to play — a loaded reconstruction, a loaded instruction, the song of an open project —
and otherwise whatever source is engaged. The Main tab plays only previews, so its target is always
the source engaged elsewhere, if any.

In one line: the transport controls the tab you are on when it has something to play, and otherwise
controls what is already sounding.

Starting a tab's idle source takes the device over, from a preview or from a source engaged
elsewhere, and Stop is how to silence background audio and leave the device idle. Play passes over a
sounding preview whenever the active tab has a source of its own, so a preview answers to Stop alone.

## The verbs

The transport's verbs are reached identically from the Playback menu, the toolbar, and the keyboard:

| Key | Command | Behaviour |
|-----|---------|-----------|
| `Space` | Play / Pause | Acts on the target: pauses or resumes it while it is engaged, and starts it from the beginning otherwise. With no target, it does nothing. |
| `Shift+Space` | Play from start | Starts the active tab's source from the beginning. |
| `Ctrl+Space` | Play from this frame | Sequencer: plays the song from the first row of the frame the tracker shows. |
| `Ctrl+Shift+Space` | Play from here | Sequencer panels: plays the song from the cursor's row. |
| `Escape` | Stop | Silences everything — the engaged source and any preview — from any tab. |

Because the target prefers the active tab's own source, `Space` controls what the user is looking at
whenever that screen can play something, and reaches the source already sounding on a screen that
plays nothing of its own: the Main tab, an empty Reconstruction or Instructions tab, the Sequencer
before a project is open. So a paused reconstruction resumes with `Space` from the Main tab, while
`Space` on the Sequencer with a project open starts the song.

## What the surfaces show

The toolbar's transport strip and the Playback menu describe the target. The Play/Pause/Resume label
and the paused indicator report what the toggle will do; Stop is available while any sound is on the
device, engaged or previewed. So the display carries across tabs that play nothing of their own,
showing the source sounding elsewhere, and shows the local source on tabs that have one. A verb
tied to one screen — playing from the shown frame — is offered on that screen with its document
open.

## Keyboard delivery under field focus

Playback keys arrive through the application's single key handler (architecture §12). These rules
keep them predictable:

**Focus is claimed per key.** A focused input keeps the keys it genuinely consumes and yields the
rest. A text or number field consumes `Space` and `Shift+Space` (space is a character it types) and
`Escape` (which cancels the field), so those keys serve the field while it holds focus. A modified
combination stays global and fires from anywhere, which is why playing from the shown frame works
while typing. Playing from the cursor row belongs to the grid: the sequencer grid claims it while the
grid itself holds the keyboard.

**Interactive widgets release the keyboard.** A selectable cell or a transport button hands focus
back after its click, so the next playback key reaches the router. This keeps `Space` and `Escape`
live in the moment after any click.

## Silencing channels

The sequencer's tracker channels can be silenced for listening. One mute set holds the silenced
channels for the open document, and everything else is derived from it: the **active-channel mask**
the song mixes through, and solo — soloing silences the other channels and remembers the mix it
replaced, so soloing the same channel again returns to that mix. Deriving both from one set is what
keeps the gestures consistent: any way of reaching "silence the rest" leaves the same state as any
other.

Every surface shows that one set and switches it. In the tracker a channel recedes down its column;
in the order table it recedes along its row; both take their shades from one pair of colours, so a
silenced channel looks the same wherever it appears. A channel's name is the switch in both tables —
click to silence, modified click to solo, the master name for the whole mix — and both tables hand
the gesture and its right-click menu to one object, so both offer the same wording and the same
behaviour. The Playback menu's **Channels** submenu carries the same set as a check per channel, plus
one item that returns the whole mix. Each of those items is registered as an action whether or not a
key is bound to it, so the keybindings options can assign one and the menu lists it.

The mask is pulled per rendered row, which is principle 6 for this control: a channel drops in or
out as the render-ahead buffer drains, with the immediacy every other live edit has. A silenced
channel still takes each row's instrument, transpose, and volume, so returning it to the mix resumes
on the state its pattern has reached.

Muting is monitoring, and principle 5 governs what follows. The project holds every channel,
so saving, module export, and any rendered output write the full song. The history stack holds
project state alone, so undo, redo, and history jumps carry the mute set across untouched — which
means the sequencer distinguishes a history restore from a document transition. And the mute set
belongs to the listening session, so opening, creating, or closing a document starts a fresh one
with every channel audible.

## Who governs what

| Concern | Owner |
|---------|-------|
| The device, its stream, and arbitration between requests | `AudioDeviceManager` (`sampletones_core/audio/`) |
| The ranking that settles a contest for the device | `PlaybackPriority` (`logic/shared/`) |
| The verbs, target resolution, and the registry of sources | `coordinators/playback/router.py` |
| A source's engagement reporting | the transport's player protocol, implemented per source |
| Error presentation for a source's failures | `GuardedPlayer` (`coordinators/playback/guard.py`) |
| Keyboard delivery, priority, and field focus | `utils/gui/keyboard/` (architecture §12) |
| The sequencer's mute set, its mask, and solo | `SequencerChannelsLogic` (`logic/sequencer/channels.py`) |
| A channel name's gestures and menu, in either table | `ChannelSwitch` (`ui/panels/sequencer/channels.py`) |
| Row mixing, and the mask it pulls while rendering | `RowSynthesizer` (`logic/sequencer/playback/synthesizer.py`) |
| The song's render-ahead buffer | `services/song_player/` |

The sequencer song is an ordinary intentional source alongside the reconstruction and instruction
players: it implements the same protocol and is arbitrated by the same rules.
