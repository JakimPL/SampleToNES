# Playback and Transport

This document governs sound across the application: what may be heard, who decides, and what each transport command means. Consult it when adding audio a user can start, a surface that starts it, or a control over what is heard. The contracts here bind every tab and every player. It complements [`architecture.md`](../architecture.md), [`keyboard.md`](keyboard.md) (which owns the keyboard-routing layer) and [`guidelines.md`](../guidelines.md).

Two terms recur. A **source** is what plays one kind of audio: a reconstruction, an instruction or the sequencer song. The **transport** is the shared play, pause and stop control over them.

---

## Principles

1. **The output is one scarce resource, arbitrated by intent.** There is a single device, a single stream and a single thing sounding. Audio a user asked a tab to play outranks audio a click auditioned. Every request says which kind it is, and the arbiter decides what is heard, not the caller's eagerness.
2. **Ownership is the state.** Which source owns the live stream is the one fact that says what is playing. Commands, labels and indicators all derive what they do and show from it, so they agree by construction.
3. **A command addresses one target, resolved from where the user is.** Context decides which source a verb means, and one resolution serves every verb. The same key therefore means the same thing on a given screen every time.
4. **Surfaces describe the target, and the transport decides.** The menu, the toolbar and the keyboard reach identical verbs and report identical state, so a new surface adds another way in to the same behavior.
5. **Listening choices stay out of the document.** What the user chooses to hear is session state, and what the project holds is the whole song. Saving, export, rendering and history read the document, so each of them works on the full song whatever the user is listening to. A render reads the document as it stood when it was asked for: every channel sounding, at unity gain, played through once.
6. **Live state is pulled while sound is produced.** A player reads the settings that shape its sound as it renders, so a change is heard as the render-ahead buffer drains. A listening control therefore takes effect inside the sound already playing.
7. **A row's duration belongs to the song, not to the player.** How long a row lasts follows from the project's tempo and meter together with the row's place in the pattern. It is a function of position: the same row lasts the same time however playback reached it, and a module exported from the song can state the same figures. The integer tick counts the [groove](../../glossary.md#groove) places *are* the tempo, so a render realizes them exactly at every rate it offers.

## Two kinds of sound

**Preview** is a quick audition fired by a click or a key: a file or reconstruction in a browser tree, a voice in the sequencer, or the instrument the Reconstructions tab has open, sounded at the note a piano key names. A preview is ephemeral. It sounds once, holds the device without claiming ownership of it, and is meant to be heard and forgotten. It yields the device to intentional playback, and it answers to Stop.

An instrument's audition is a preview of that kind. It reads the generator chosen on the instruments card, takes the note from the keyboard's two octaves above the octave the tracker types in, and renders the voice through the same two steps a tracker row takes: the step from the instrument's own pitch to the note, at full volume. The plot card draws the same rendering at the pitch the instrument stands at, so what is seen and what is heard name one generator.

**A preview sounds the frames it renders.** An instrument sounds the envelopes it has, and a sample previews the frames its reconstruction recorded. Both sound exactly what they carry, because a recording's drive matters only while the conversion runs.

**A voice sounded on its own runs to its release, or to the length it is offered.** A row holds a voice for as long as the pattern asks. An audition and the voice list's preview have no row behind them, so each has a span of its own. A volume dimension that ends at silence releases the voice, and the sound stops there. A voice that circles from a loop point never reaches a last item, so it sounds for the ticks `AUDITION_TICKS` offers it. `audition_ticks` (`sampletones_core/performance/audition.py`) counts both spans, so the plot card draws exactly the frames the keyboard sounds.

**A sounding voice is marked where it has reached.** The device reports its position while it plays, and the plot card carries that mark along the voice it drew, as it does for a reconstruction's playback. A preview follows its own sound alone: `play` reports whether the request took the output, and the audition starts following only when it did. A request that yields to playback the reader asked for leaves that playback's mark where it is. The device reports a final zero as it winds down, which takes the mark off the card.

A report comes from the thread writing the audio, and the mark is a widget, so every report crosses to the render thread before it moves anything (architecture principle 6). A source's player reads where its own playback stands when the report arrives. A seek made in the meantime therefore stands: the mark shows the device as it is, and a report that set out before the seek draws the seek.

**Intentional playback** is the audio a tab is built around: a reconstruction's audio, an instruction's audio or the sequencer song. The source that started it owns it, and it is resumable, seekable and stoppable. At most one intentional source is engaged at any moment.

Priority ranks the two kinds and settles every contest for the device. Starting intentional playback preempts a sounding preview, and a preview requested while intentional playback holds the device is declined.

## Engagement

A source is **engaged** while it owns the device output, whether it is sounding or held paused. A source therefore reports itself engaged only while *its own* audio is the one on the device. While a preview sounds, ownership rests outside every source and each of them reports itself idle.

Engagement is the ownership test of principle 2 in practice, and it is the single fact the transport and the toolbar consult.

## The target

The transport acts on one **target**, resolved in two steps. The active tab's own source is the target when that tab has one to play: a loaded reconstruction, a loaded instruction or the song of an open project. Otherwise the target is whatever source is engaged. The Main tab plays only previews, so its target is always the source engaged elsewhere, if any. The transport thus controls the tab you are on when it has something to play, and otherwise controls what is already sounding.

Starting a tab's idle source takes the device over, from a preview or from a source engaged elsewhere. Stop silences background audio and leaves the device idle. Play passes over a sounding preview whenever the active tab has a source of its own, so a preview answers to Stop alone.

## The verbs

The transport's verbs are reached identically from the Playback menu, the toolbar and the keyboard:

| Command | Behavior |
|---------|-----------|
| Play / Pause | Acts on the target: pauses or resumes it while it is engaged, and starts it from the beginning otherwise. With no target, it does nothing. |
| Play from start | Starts the active tab's source from the beginning. |
| Play from this frame | Sequencer: plays the song from the first row of the frame the tracker shows. |
| Play from here | Sequencer panels: plays the song from the cursor's row. |
| Stop | Silences everything, the engaged source and any preview, from any tab. |

Each verb is an action, so the combination it answers to is the shipped scheme's (`sampletones_config/keybindings/`) and every surface prints what the scheme says.

**A click on a waveform puts the playhead at a sample.** The Reconstructions and Instructions waveforms draw the audio their tab's own source plays, so a click reaches that source at the sample under the pointer. An engaged source moves there and goes on sounding or stays paused, and an idle one starts sounding there. The seek and the ownership it depends on are read under one lock, so a source another has taken the output from starts sounding and does not move a playback it lost. A waveform that draws a voice's own audio draws nothing its player sounds, so it takes no click and its hint names none.

The left button carries three gestures: a click seeks, a drag pans the view, and a double-click fits it to the audio. `PlotClickGesture` (`ui/elements/graphs/gesture.py`) settles which one a press was, so the playhead and the view each answer only the gesture meant for them.

The wheel carries the view too. Scrolling zooms x, and Shift with the wheel zooms y. Alt with the wheel pans x, and Alt and Shift pan y, by `pan_factor` of the span in view per notch, stopping at the bounds the graph constrains its axes to. `PlotWheelPan` (`ui/elements/graphs/pan.py`) makes those moves. `GUIGraph` locks both axes on every hover frame Alt is held, so the plot's own zoom leaves the wheel to the pan, and a lane linked to the waveform holds the same lock. The spectrum, whose view is fixed to its band, does not register the pan.

Because the target prefers the active tab's own source, Play/Pause acts on what the user is looking at whenever that screen can play something. On a screen that plays nothing of its own, it reaches the source already sounding. Those screens are the Main tab, an empty Reconstruction or Instructions tab, and the Sequencer before a project is open. So it resumes a paused reconstruction from the Main tab, and starts the song on the Sequencer with a project open.

## What the surfaces show

The toolbar's transport strip and the Playback menu describe the target. The Play/Pause/Resume label and the paused indicator report what the toggle will do. Stop is available while any sound is on the device, engaged or previewed. The display therefore carries across tabs that play nothing of their own, showing the source sounding elsewhere, and shows the local source on tabs that have one. A verb tied to one screen, such as playing from the shown frame, is offered on that screen with its document open.

The sequencer view reports the playhead too, at the reach the **follow mode** chooses: the sounding row, the frame that holds it, or the view the user placed. The mode is one setting with two derived answers: whether the tracker shows the frame being played, and whether it scrolls to keep the sounding row in sight. Those two are its whole contract, and every surface that follows the playhead reads them. The song player holds the mode and emits it with every position, so the menu's check and the grid's scrolling settle in one step when the mode changes mid-playback.

A mark belongs to what it names. The playhead's position is a frame and a row within it. The order grid marks the frame under every mode. The row's mark reads as the sounding row of the pattern on screen: the tracker carries it while the frame it shows is the frame that sounds, and the mark travels with the frame across a structural order edit. Every mode paints on this rule, and the mode governs where the view sits.

## Keyboard delivery

Playback keys arrive through the application's single key handler (architecture principle 12). [`keyboard.md`](keyboard.md) describes how a focused field claims some of them and yields the rest.

## Silencing channels

The sequencer's tracker channels can be silenced for listening. One mute set holds the silenced channels for the open document, and everything else derives from it: the **active-channel mask** the song mixes through, and solo. Soloing silences the other channels and remembers the mix it replaced, so soloing the same channel again returns to that mix. Deriving both from one set keeps the gestures consistent, because any way of reaching "silence the rest" leaves the same state as any other.

Every surface shows that one set and switches it. A channel's name is the switch in both the tracker and the order table: click to silence, modified click to solo, the master name for the whole mix. Both tables hand the gesture and its right-click menu to one object, so they offer the same wording and the same behavior, and both take their shades from one pair of colors. The Playback menu's **Channels** submenu carries the same set as a check per channel, plus one item that returns the whole mix. Each of those items is registered as an action whether or not a key is bound to it, so the keybinding scheme can give it one and the menu prints what the scheme says (architecture principle 12).

The mask is pulled per rendered row, which is principle 6 for this control: a channel drops in or out as the render-ahead buffer drains, with the immediacy every other live edit has. A silenced channel still takes each row's voice, transpose and volume, so returning it to the mix resumes on the state its pattern has reached.

Muting is monitoring, and principle 5 governs what follows. The project holds every channel, so saving, module export and any rendered output write the full song. The history stack holds project state alone, so undo, redo and history jumps carry the mute set across untouched. That is why the sequencer distinguishes a history restore from a document transition. The mute set belongs to the listening session, so opening, creating or closing a document starts a fresh one with every channel audible.

## What the channel holds

A sample has a value for every dimension of every frame, and its reconstruction names the dimensions the channel governs. The instrument writes the rest itself. Each channel carries a value per dimension (volume, arpeggio, timbre), and an instrument that leaves one empty sounds it at the value the channel holds. That is what clearing an envelope in the instruments panel means once the sample is played in a song. A FamiTracker instrument follows the same rule with a sequence left out.

The value moves as the song plays. Every frame an instrument writes hands its value to the channel, so the channel keeps the last one written, and an instrument that leaves the dimension empty picks it up. A silent frame sets its level alone and leaves pitch and timbre where the channel holds them.

A pass through the song begins on the values a channel holds from the start: full volume, no arpeggio offset, the first timbre. Starting the song and looping back to its first row therefore sound the same. Seeking within a running song keeps the values, since the channel has reached them.

## Rendering the song to a file

A render writes the whole song to an audio file through the synthesizer that plays it. `RowSynthesizer` serves both: the player drives it to feed the device, and the render drives it to feed a file writer. The synthesis is therefore written once, and the file and the playback agree on what the song sounds like by construction.

Two things differ between them, and whoever asks for the audio sets each. The **document** is read through an interface. The synthesizer reads its project through `ProjectSource`, which the live controller satisfies for playback and a frozen `ProjectSnapshot` satisfies for a render. The player therefore follows every edit as the buffer drains (principle 6), while a render describes one state of the document however the project moves on. The **rate** is the consumer's: the device for playback, the chosen output format for a render. The synthesizer rebuilds its generators and its tick clock when either changes, so a file is written at the rate its engine ran at.

A rate is asked for once there is audio to take it, which is the first row the synthesizer renders. A device has been chosen by the time playback starts, and a format by the time a render does. A session on a machine with no output device opens on that rule, and everything that writes and does not sound works on it: editing, exporting a module and rendering to a file.

The song's exact length follows from the timing model before a sample is rendered. The order's length in rows gives the ticks, and the tick clock gives the samples those ticks span. That figure is what the progress bar counts against and what a finished file measures.

Rendering is an exclusive operation (architecture principle 10). It occupies the application from the moment its dialog opens until that dialog closes. It joins the same busy authority as conversion and library generation, so each of the three holds the others off and every surface offering one reads a single answer.

The write takes one pass, or two where the user asks for a normalized peak. The first pass spills raw samples and discovers the peak, and the second reads them back and encodes at the scale that peak sets. Each pass names itself, so the bar crosses one axis, samples, twice, and holds a single unit across both. A cancel is honored between rows and between encoded blocks. A render that is stopped or fails clears the destination and the spill, so a path in a result always names a finished file.

## Teardown

The device is torn down once every source holding a stream has released it. A source that streams to the device writes from a thread of its own, so only that source can bring the writing to a stop and hand the stream back. The hand-back is what leaves the backend safe to terminate.

`PlaybackRouter.shutdown()` is the entry point the application calls as it quits. It reaches every registered source and not only the engaged one, so a source holding a stream is wound down whatever the transport reports at that moment.

The device holds a release per stream it handed out and invokes it whenever it needs the output free: as the backend is torn down, and on a device change, where the release stops the song so the new device opens cleanly. A stream that outlives its release leaves the running backend in place. The manager reports the failure and keeps the instance, since the source still writes to memory that terminating would reclaim.

## Who governs what

| Concern | Owner |
|---------|-------|
| The device, its stream, and arbitration between requests | `AudioDeviceManager` (`sampletones_core/audio/`) |
| The ranking that settles a contest for the device | `PlaybackPriority` (`logic/shared/`) |
| The verbs, target resolution, and the registry of sources | `coordinators/playback/router.py` |
| A source's engagement reporting | the transport's player protocol, implemented per source |
| Error presentation for a source's failures | `GuardedPlayer` (`coordinators/playback/guard.py`) |
| The sequencer's mute set, its mask, and solo | `SequencerChannelsLogic` (`logic/sequencer/channels.py`) |
| Row mixing, and the mask it pulls while rendering | `RowSynthesizer` (`logic/sequencer/playback/synthesizer/`) |
| The values a channel holds between frames | `ChannelState` (`logic/sequencer/playback/synthesizer/state.py`) |
| How long a row lasts, and how many samples its ticks span | `Groove` and `TickClock` (`sampletones_core/timing/`) |
| Rendering the song to a file, its passes and its progress | `SongRenderService` (`services/render/`) |

The sequencer song is an ordinary intentional source alongside the reconstruction and instruction players. It implements the same protocol and is arbitrated by the same rules.
