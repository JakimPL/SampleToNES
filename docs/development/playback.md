# Playback and Transport

This document defines how audio playback behaves across the application: what can sound, who
controls it, and what each transport command and shortcut does. It is prescriptive — the contracts
here bind every tab and every player. It complements `docs/development/architecture.md` (which owns
the keyboard-routing layer, §12) and `docs/development/guidelines.md`.

---

## One output, two kinds of sound

The application drives a single shared output device (`AudioDeviceManager`,
`sampletones_core/audio/manager.py`): one stream, one thing sounds at a time. Every request carries
a **priority** and an **owner**, and a higher-priority request takes the device over.

Audio comes in two kinds:

**Preview** — a quick audition fired by a click (a file/reconstruction in a browser tree, a sample
in the sequencer). A preview is *ephemeral*: it plays once at `PREVIEW` priority, owned by nobody,
and is meant to be heard and forgotten. Stop silences it. It yields the device to intentional
playback.

**Intentional playback** — the audio a tab is built around: a reconstruction's audio, an
instruction's audio, or the sequencer song. It plays at `NORMAL` priority, owned by the source that
started it, and it is resumable, seekable, and stoppable. **At most one** intentional playback is
engaged at any moment.

`PlaybackPriority` (`logic/shared/playback_priority.py`) ranks them: `PREVIEW (0) < NORMAL (1)`.
Starting intentional playback preempts a sounding preview; a preview requested while intentional
playback holds the device is dropped.

## Engagement is decided by ownership

An intentional source is **engaged** when it currently owns the device output — whether it is
sounding or held paused. Engagement is read from **ownership** (`AudioDeviceManager` tracks the
owner of the live stream), so a source reports itself engaged only while *its own* audio is the one
on the device. A sounding preview leaves every intentional source disengaged.

This ownership test is the single fact the transport and the toolbar read to decide what
a command controls.

## The transport target

The transport acts on a single **target**: the active tab's own source when that tab has one to
play — a loaded reconstruction (Reconstruction tab), a loaded instruction (Instructions tab), or the
song (Sequencer tab with a project open) — and otherwise the engaged intentional source, if any. The
Main tab owns only previews, so its target is always whatever is engaged elsewhere, or nothing.

In one line: the transport controls the tab you are on when it has something to play, and otherwise
controls whatever is currently sounding.

## Transport commands

The transport exposes five verbs, reached identically from the Playback menu, the toolbar buttons,
and the keyboard. The keyboard scheme:

| Key | Command | Behavior |
|-----|---------|----------|
| `Space` | Play / Pause | Act on the target: pause or resume it when it is engaged, otherwise start it from the beginning. With no target, do nothing. |
| `Shift+Space` | Play from start | Start the active tab's source from the beginning. |
| `Ctrl+Space` | Play from this frame | Sequencer only: play the song from the frame the tracker is showing (row 0). |
| `Ctrl+Shift+Space` | Play from here | Sequencer panels only: play the song from the cursor's row. |
| `Escape` | Stop | Silence everything — the engaged intentional source **and** any preview — from any tab. |

Because the target prefers the active tab's own source, `Space` controls what you are looking at
whenever that tab can play something, and falls back to the source already sounding only on a tab
that owns nothing of its own — the Main tab always, an empty Reconstruction or Instructions tab, or
the Sequencer without a project. So a paused reconstruction resumes with `Space` from the Main tab,
while `Space` on the Sequencer with a project open starts the song.

Starting a tab's idle source takes the device over from a preview or from a source engaged
elsewhere. To silence a source that is sounding in the background without starting a new one, use
`Escape`.

Previews answer only to Stop: `Space` addresses the target, so a sounding preview — which no source
owns — is passed by whenever the active tab has its own source. Every tab treats a preview the same
way; no tab owns a preview.

## Toolbar and menu state

The toolbar transport strip and the Playback menu describe the **target**: the Play/Pause/Resume
label and the paused indicator report what the toggle will do. Stop is available whenever any sound
is on the device — an engaged source or a preview. So the transport display persists across tabs
that own no source (showing the source sounding elsewhere) and shows the local source on tabs that
do. "Play from this frame" is available only on the Sequencer tab with a project open.

## Keyboard delivery and field focus

The transport keys reach the application through the single `KeyRouter` handler
(`utils/gui/keyboard/`, architecture §12). Two rules keep them predictable:

**Focus is per-key.** A focused input keeps only the keys it actually consumes. A text or number
field takes `Space` and `Shift+Space` (space is a character it types) and `Escape` (which cancels
the field), so those reach the field while it is focused. `Ctrl+Space` is never a field character,
so this global shortcut always fires, even while a field is focused. `Ctrl+Shift+Space` is not a
global shortcut but a grid action: the sequencer grid claims it only while the grid — not a field —
holds the keyboard, so it plays from the cursor row when you are editing the grid and stays inert
while a field is focused. Field-transparent shortcuts (tab switching) fire whether or not a field is focused.

**Interactive widgets do not hold the keyboard.** After a click, a selectable cell or a transport
button releases keyboard focus, so a transport key is delivered to the router rather than being
absorbed by the focused widget. This keeps `Space` and `Escape` working the moment after any click.

## The channel mask

Each of the sequencer's four tracker channels can be silenced for listening. `SequencerChannelsLogic`
(`logic/sequencer/channels.py`) owns the mute set for the open document and derives the
**active-channel mask** — the channels that sound — from it. Solo is derived from the same set:
soloing silences the other three and remembers the set it replaced, so a second solo of that channel
returns to the mix it interrupted.

The mask is **pulled per row**. `RowSynthesizer` reads it through a provider callable while mixing
each row, so a change during playback is heard as the render-ahead buffer (`PREFETCH_SECONDS`)
drains — the same immediacy every other live edit has. A silenced channel still takes each row's
instrument, transpose, and volume, so unmuting resumes on the state the pattern has reached.

Muting is **monitoring only**, and three consequences follow. The project holds every channel, so
saving, `.ftm` export, and any rendered output write the full song. The history stack holds project
state alone, so undo, redo, and history jumps carry the mute set across untouched — the sequencer
coordinator reads `HistoryManager.is_restoring` to tell those apart from a document transition. And
the mute set belongs to the listening session, so opening, creating, or closing a document starts it
fresh with every channel audible.

## Where this lives in code

A single transport (`coordinators/playback/`) holds the intentional sources and the resolver for
the active tab's source, and implements the verb matrix above. Each intentional source implements
the transport's player protocol with ownership-aware `is_playing`/`is_paused`; error presentation
stays in `GuardedPlayer`. The sequencer song is an ordinary intentional source alongside the
reconstruction and instruction players.
