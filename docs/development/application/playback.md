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
7. **A row's duration belongs to the song, not to the player.** How long a row lasts follows from the project's tempo and meter together with the row's place in the song. It is a function of position: the same row lasts the same time however playback reached it, and a module exported from the song can state the same figures. The integer tick counts the [groove](../../glossary.md#groove) places *are* the tempo, so a render realizes them exactly at every rate it offers.

## Two kinds of sound

**Preview** is a quick audition fired by a click or a key: a file or reconstruction in a browser tree, a voice in the sequencer, or the instrument the Reconstructions tab has open, sounded at the note a piano key names. A preview is ephemeral. It sounds once, holds the device without claiming ownership of it, and is meant to be heard and forgotten. It yields the device to intentional playback, and it answers to Stop.

An instrument's audition is a preview of that kind. It reads the generator chosen on the instruments card, takes the note from the keyboard's two octaves above the octave the tracker types in, and renders the voice through the same two steps a tracker row takes: the step from the instrument's own pitch to the note, at full volume. The plot card draws the same rendering at the pitch the instrument stands at, so what is seen and what is heard name one generator.

**A preview sounds the frames it renders.** An instrument sounds the envelopes it has, and a sample previews the frames its reconstruction recorded. Both sound exactly what they carry, because a recording's drive matters only while the conversion runs. A sample's preview sounds the render the render cache keeps, or the one a worker of its own lands a moment later, so the render thread computes no sample for it; a newer click replaces a preview still on its way, and playback the reader starts forgets one, so the voice heard is the last one asked for and a song started meanwhile keeps the device. A reconstruction a browser tree plays is read from disk and previewed the same way.

**A voice sounded on its own is a live note, and sounds what a row holding its pitch sounds.** A live note (`LiveNote`, `sampletones_core/performance/live.py`) starts each channel at the step the key's pitch asks of the voice's reference, plays every tick through the step a row's tick takes, and a release silences it as a note-off does. An instrument reads a key as a note and a sample as a step, which are the faces a pitch cell reads in for each kind of voice. The audition, the plot card and the voice list's preview all sound live notes, so each reads a voice the way the song does, the dimensions it leaves empty included.

**A voice sounded on its own runs to its release, or to the length it is offered.** A row holds a voice for as long as the pattern asks. An audition and the voice list's preview have no row behind them, so each has a span of its own. A volume dimension that ends at silence releases the voice, and the sound stops there. A recording runs out once its frames are played. A voice that circles from a loop point never reaches a last item, so it sounds for the ticks `AUDITION_TICKS` offers it. One count serves both spans, so the plot card draws exactly the frames the keyboard sounds.

**Keys played live are one preview for as long as they are played.** One owner, `LiveKeysLogic` (`logic/shared/live/`), takes every key from either keyboard. The first press claims the output at the preview rank through the preview player, so Stop silences it, the song declines it, and it takes the output from another preview. Every later press, lift and pedal change reaches that playback as a command, so keys played one after another sound on one stream. A key lifted after a stop or a takeover reaches nothing.

**One note sounds at a time, and the newest press is it.** Lifting that key returns to the most recent key still held, which strikes again, and lifting a key behind it changes nothing heard. A lift ends an instrument's note on either keyboard. A MIDI key ends a recording as it lifts, and a computer key lets a recording play to its end. The sustain pedal keeps a lifted note sounding until the pedal comes up. The pedal's state belongs to the pedal, so a playback started while it is down starts sustained.

**Each strike starts afresh.** A strike starts its note at the next block, on a tick grid of its own, with its generators at rest, so it sounds as a row starting that note does. A lift ends the note at the next block. Each sound carries the settings its voice is synthesized under, so a recording converted at another tick rate keeps its pace.

**The keys' playback lingers.** Once no key is down and no note sounds, the source plays `LIVE_LINGER_SECONDS` of silence before it ends. A press during the linger is heard after the audio the device has ahead. A press with nothing playing first waits for a writer to start, a stream to open and the generators to be built, and that wait grows with the render loop's load. The linger therefore keeps a phrase's timing steady, and the phrase opens one stream. `tests/benchmarks/test_live_keys.py` measures both waits.

**A key reaches the sound from the thread its keyboard reports on.** A computer key arrives on the render thread and a MIDI key on the MIDI thread. Each call is decided under the owner's lock and becomes a command the writer runs between two reads, so both keyboards can play at once. The preview player decides each claim and its stop under a lock of its own, so Stop always reaches the latest preview, whichever thread claimed it.

**A sounding voice is marked where it has reached.** Its playback reports each position the device took, and the plot card carries that mark along the voice it drew, as it does for a reconstruction's playback. A preview follows its own playback alone: `play` answers with the playback, or with nothing where the output declined the request, and the audition follows only a playback it holds. A declined request leaves the holder's mark where it is. The playback's end report takes the mark off the card.

A report comes from the thread writing the audio, and the mark is a widget, so every report crosses to the render thread before it moves anything (architecture principle 6). An owner hears only the playback it holds, so a report from a sound it let go of moves nothing. A seek travels to the source as a command between two reads, and a position read before the owner's latest command is dropped as it lands, so a mark drawn after a seek reads the seek.

**Intentional playback** is the audio a tab is built around: a reconstruction's audio, an instruction's audio or the sequencer song. The source that started it owns it, and it is resumable, seekable and stoppable. At most one intentional source is engaged at any moment.

Rank settles every contest for the device. Intentional playback claims at the higher rank, and so does a preview the reader asks for by name, such as Play on a voice's row or on a file. A preview that a selection or a key fires, such as autoplay or an audition, claims at the lower rank. A claim ranked below the holder is declined, and any other takes the output. Starting intentional playback therefore ends a sounding preview, a preview asked for by name ends whatever sounds, and an autoplay is declined while intentional playback holds the device. A sound holds the output from its claim, before its stream opens, so every contest is settled at the moment of asking, and the sound that lost hears its end at once.

**A sound starts only on a device in force.** The output refuses a claim with `NoOutputDeviceError` when no device is in force, before a thread or a stream opens. One presenter, `PlaybackFailurePresenter` (`coordinators/playback/failures.py`), tells the reader what stopped any sound: a missing output reads as a plain notice, and every other failure as an error. A failure on the thread playing the sound, such as a stream the device refused or a write it failed, reaches the owner as its playback's end report. It reads the same whichever source played it, and is told once.

## Engagement

A source is **engaged** while its playback holds the output, from the claim until its end is decided, whether it is sounding or held paused. A source therefore reports itself engaged only while *its own* audio is the one on the device. While a preview sounds, ownership rests outside every source and each of them reports itself idle.

Engagement is the ownership test of principle 2 in practice, and it is the single fact the transport and the toolbar consult.

## The output contract

Every sound on the device answers to the rules below, whatever its kind and whoever started it. A **playback** is one sound, from the moment it asks for the output until it ends. Its **owner** is what started it. A source owns its intentional playback, and one preview owner plays and owns every preview. Each playback case names the rule it holds.

1. **A claim ranked below the holder is declined, and any other claim takes the output.** Claims made at the same moment leave one holder.
2. **The device holds at most one open stream.** A stream opens once the one before it has closed.
3. **Every playback sends exactly one end report, and the report names its cause:** the sound finished, its owner stopped it, another sound took the output, or it failed. Once the report lands, the output is free of the playback, and the device has already received its last sample.
4. **Positions are reported per playback, in order, for audio the device has received.** They arrive before the end report. A position read after a seek reads the seek. A playback that has ended refuses a seek, so its owner starts a new one.
5. **A sound plays at its own pitch and length on a device of any rate.**
6. **Stop silences everything, and the call returns at once.** A natural end plays the tail out, and a stop or a takeover cuts it.
7. **A failure is told once,** to its owner's listener.
8. **After teardown, every audio thread has ended and every stream is closed.** The teardown reports a thread that outlives its deadline, and a writer among them keeps the backend alive.

The integration suite under `tests/integration/sampletones_application/playback/` holds every sound to these rules through the application's own owners, and a seeded storm (`tests/unit/sampletones_core/audio/output/test_storms.py`) holds the output to them under owners acting at once over a device that is slow and fails.

## The audio output

Every sound plays through one `AudioOutput` (`sampletones_core/audio/output/`), which holds the device's one stream and the backend under it. An owner hands the output an **audio source**, which the output reads a block at a time, and the rank it claims at. The owner then holds the **playback** the output answers with.

**One path carries every sound.** The playback is the owner's handle on the sound, from its claim to its end report. The owner pauses, resumes, stops and commands the sound there, and hears of it through its listener. Every rule of the contract therefore holds for every kind of sound through one implementation, and each part of the path is tested alone against a fake device.

**A playback is the identity of one sound.** Each start makes a new playback, and an owner listens only to the playbacks it holds. A late report from a sound the owner let go of finds no holder, so a newer sound keeps its mark and its state.

**Requests are decided at once, and one thread calls the device.** A claim, a stop, a pause and a device change are decided under the output's lock as they arrive, so the render thread waits on no device (architecture principle 6). One writer thread carries the decisions out: it opens the stream, reads a block from each playback, writes the mix, and drains or cuts the stream. Every device call runs outside the lock, so a device slow to answer holds that thread alone. The writer starts with the request that gives it work and ends once nothing is left, so an idle application runs no audio thread.

**The decisions are pure state machines.** `SessionCore` and the lifecycles it holds decide each step from the events before it alone, so a case drives them directly. A model check drives them through every order of events up to a bound and holds each order to the contract. The output's lock and its waking of the writer are all the threads add.

**Every claim plays on a stream of its own.** A claim made while a stream is open cuts that stream, and the new sound opens the next one. A stream therefore carries one sound from its opening to its close, and a takeover cuts the tail by closing that sound's stream (rule 6). A paused playback keeps its stream, and the writer sleeps beside it until a request arrives, so a pause costs nothing while it lasts and a resume plays on at once.

**An audio source learns the stream's rate as it begins.** The writer begins each source at its first read with the rate of the stream it plays on, so a sound always plays at the rate the device takes (rule 5). Document audio keeps its own rate in a `BufferSource`, which resamples it as it streams and reports positions in document samples. The song builds its synthesizer for the stream's rate.

**A source is read on the writer's thread alone.** An owner's command, such as a seek or a new buffer of audio, runs there between two reads, so every read and every command of a source runs on one thread, in order. A source failing on a thread of its own, such as the song's renderer, tells its playback through the failure report it was begun with, which ends the playback at once, sounding or paused. A read fails however the source's code fails, so the writer catches the read whole: the failure ends that playback as its end report, and every other playback plays on.

**Every report crosses in the order it was made.** The output hands each report to the post it was built with. The application posts through the callback queue at one priority, so an owner hears its positions in order and its end report last.

**Each sound carries its own level.** The mix sums the blocks the playbacks fill and clips the sum to full scale. A level belongs to the sound it shapes: the song reads the master gain for every block it hands the device, so a move of the slider is heard from the next block.

**A sound starts and ends on one device.** A new device or rate ends every playback as stopped, and the next sound opens on the new settings. A new buffer size reaches the next stream, so a sound playing carries on. A refresh renews the backend on the writer's thread while no stream is open, finds the device in force again by its name, and hands the devices it lists to the render thread.

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

**A click on a waveform puts the playhead at a sample.** The Reconstructions and Instructions waveforms draw the audio their tab's own source plays, so a click reaches that source at the sample under the pointer. An engaged source moves there and goes on sounding or stays paused, and an idle one starts sounding there. The seek is a command to the source's own playback. A playback another sound took refuses it, so the source starts a new playback at that sample, and the sound it lost stays where it was. A waveform that draws a voice's own audio draws nothing its player sounds, so it takes no click and its hint names none.

The left button carries three gestures: a click seeks, a drag pans the view, and a double-click fits it to the audio. `PlotClickGesture` (`ui/elements/graphs/gesture.py`) settles which one a press was, so the playhead and the view each answer only the gesture meant for them.

The wheel carries the view too. Scrolling zooms x, and Shift with the wheel zooms y. Alt with the wheel pans x, and Alt and Shift pan y, by `pan_factor` of the span in view per notch, stopping at the bounds the graph constrains its axes to. `PlotWheelPan` (`ui/elements/graphs/pan.py`) makes those moves. `GUIGraph` locks both axes on every hover frame Alt is held, so the plot's own zoom leaves the wheel to the pan, and a lane linked to the waveform holds the same lock. The spectrum, whose view is fixed to its band, does not register the pan.

Because the target prefers the active tab's own source, Play/Pause acts on what the user is looking at whenever that screen can play something. On a screen that plays nothing of its own, it reaches the source already sounding. Those screens are the Main tab, an empty Reconstruction or Instructions tab, and the Sequencer before a project is open. So it resumes a paused reconstruction from the Main tab, and starts the song on the Sequencer with a project open.

## What the surfaces show

The toolbar's transport strip and the Playback menu describe the target. The Play/Pause/Resume label and the paused indicator report what the toggle will do. Stop is available while any sound is on the device, engaged or previewed. The display therefore carries across tabs that play nothing of their own, showing the source sounding elsewhere, and shows the local source on tabs that have one. A verb tied to one screen, such as playing from the shown frame, is offered on that screen with its document open.

**A source reports its own transitions.** Each source tells the surfaces when it starts, pauses, resumes, stops or ends, whichever gesture moved it: the transport, a context menu, a key a grid owns, or the end of the sound. The surfaces therefore stay in step with a source no caller remembered to mention. A preview belongs to no source, so the surfaces read the output for it: whether any sound holds it.

The sequencer view reports the playhead too, at the reach the **follow mode** chooses: the sounding row, the frame that holds it, or the view the user placed. The mode is one setting with two derived answers: whether the tracker shows the frame being played, and whether it keeps the sounding row at the center of its band. Those two are its whole contract, and every surface that follows the playhead reads them. The song player holds the mode and emits it with every position, so the menu's check and the grid's scrolling settle in one step when the mode changes mid-playback.

A mark belongs to what it names. The playhead's position is a frame and a row within it. The order grid marks the frame under every mode. The row's mark stands wherever the tracker draws the sounding row: on the frame's own rows while the frame it shows is the frame that sounds, and on a row of the song standing beside that frame while one of those sounds. The mark travels with the frame across a structural order edit. Every mode paints on this rule, and the mode governs where the view sits.

**The tracker shows the song around the frame.** Its band keeps the row it follows at its center: the sounding row while Follow rows plays, and otherwise the cursor's row as a key carries it. Above and below the frame stand as many of the song's rows as half the band holds, each read as its own frame reads it and drawn dimmed and read-only, and blank where the song ends. Every row of the frame therefore has the room to reach the center, and one calculation places the cursor and the playhead alike. The band measures its height as the window resizes, and a new reach builds the grid again.

## Keyboard delivery

Playback keys arrive through the application's single key handler (architecture principle 12). [`keyboard.md`](keyboard.md) describes how a focused field claims some of them and yields the rest.

## Silencing channels

The sequencer's tracker channels can be silenced for listening. One mute set holds the silenced channels for the open document, and everything else derives from it: the **active-channel mask** the song mixes through, and solo. Soloing silences the other channels and remembers the mix it replaced, so soloing the same channel again returns to that mix. Deriving both from one set keeps the gestures consistent, because any way of reaching "silence the rest" leaves the same state as any other.

Every surface shows that one set and switches it. A channel's name is the switch in both the tracker and the order table: click to silence, modified click to solo, the master name for the whole mix. Both tables hand the gesture and its right-click menu to one object, so they offer the same wording and the same behavior, and both take their shades from one pair of colors. The Playback menu's **Channels** submenu carries the same set as a check per channel, plus one item that returns the whole mix. Each of those items is registered as an action whether or not a key is bound to it, so the keybinding scheme can give it one and the menu prints what the scheme says (architecture principle 12).

The mask is pulled per rendered row, which is principle 6 for this control: a channel drops in or out as the render-ahead buffer drains, with the immediacy every other live edit has. A silenced channel still takes each row's voice, transpose and volume, so returning it to the mix resumes on the state its pattern has reached.

Muting is monitoring, and principle 5 governs what follows. The project holds every channel, so saving, module export and any rendered output write the full song. The history stack holds project state alone, so undo, redo and history jumps carry the mute set across untouched. The mute set belongs to the listening session, so opening, creating or closing a document starts a fresh one with every channel audible.

## What the channel holds

A sample has a value for every dimension of every frame, and its reconstruction names the dimensions the channel governs. The instrument writes the rest itself. Each channel carries a value per dimension (volume, arpeggio, bend, timbre), and an instrument that leaves one empty sounds it at the value the channel holds. A FamiTracker instrument follows the same rule with a sequence left out.

Every note starts those values where a song starts them: full volume, no arpeggio offset, no bend, the first timbre (duty 0 on a pulse channel, the long mode on noise). A dimension the instrument leaves empty therefore sounds at that start for the whole note, whatever the note before it wrote. An empty volume plays at the row's level. FamiTracker and Bitphase start a note the same way, so an exported song plays in the tracker as it does here.

Within a note, every frame the instrument writes hands its value to the channel. A silent frame sets its level alone and leaves pitch and timbre where the note last put them.

The row's level scales the instrument's. A channel sounds their product over the full level. A pulse channel rounds it to the nearest step. The noise channel rounds it down, and sounds the quietest level wherever that comes out silent while both levels sound. FamiTracker and Bitphase set the noise level by that rule, so an exported song's noise plays there at the level it plays here. On the pulse channels the two trackers part: Bitphase rounds to the nearest step as the app does, and FamiTracker rounds down as it does on noise.

A pass through the song begins on the same values, so starting the song and looping back to its first row sound the same. Seeking within a running song keeps the values, since the sounding note has reached them.

## What a row's pitch means

A pitch cell holds what the reader typed: a note the channel sounds, or a step from the voice's own reference, on either kind of voice. The row keeps that face, and the walk resolves it when the row is played: a note sounds where it says, and a step moves the voice from where it rests. A note therefore keeps its pitch when the voice under it changes, and a step keeps its interval, which is what each face is for.

A voice placed with a pitch starts there. A sample placed without one plays as it was recorded. An instrument has no pitch of its own to sound, so one placed without a pitch restarts its envelopes on the pitch the channel is sounding, whichever voice sounded it; that is how a row retriggers a note already standing. On a silent channel it starts nothing. A channel is silent from the song's start, after a note-off, and while its voice has no frames on it; a voice whose frames have run out is still the channel's note, since no row has ended it. A pitch without a note-on moves the note already sounding and leaves a silent channel as it is.

The exports write every note at the step the walk gives it, so an instrument-only row reaches a tracker as the note it sounds here, and one that sounds nothing reaches it as an empty cell. The walk is the song's own, driven row by row through the same rule, so the two cannot drift apart.

## Rendering the song to a file

A render writes the whole song to an audio file through the synthesizer that plays it. `RowSynthesizer` serves both: the player drives it to feed the device, and the render drives it to feed a file writer. The synthesis is therefore written once, and the file and the playback agree on what the song sounds like by construction.

Two things differ between them, and whoever asks for the audio sets each. The **document** is read through an interface. The synthesizer reads its project through `ProjectSource`, which the live controller satisfies for playback and a frozen `ProjectSnapshot` satisfies for a render. The player therefore follows every edit as the buffer drains (principle 6), while a render describes one state of the document however the project moves on. The **rate** is the consumer's: the stream's for playback, the chosen output format for a render. Playback builds a synthesizer for each start at the rate of the stream that start opens, and a render builds one at its format's rate, so a file is written at the rate its engine ran at.

A rate is asked for once there is audio to take it. The song's source learns it as its stream opens, and a render as it begins. A session on a machine with no output device opens on that rule, and everything that writes and does not sound works on it: editing, exporting a module and rendering to a file.

The session keeps the device the user last applied in Audio settings. A remembered device unplugged for one run is therefore looked for again in the next, the way a remembered folder is.

The song's exact length follows from the timing model before a sample is rendered. The order's length in rows gives the ticks, and the tick clock gives the samples those ticks span. That figure is what the progress bar counts against and what a finished file measures.

Rendering is an exclusive operation (architecture principle 10). It occupies the application from the moment its dialog opens until that dialog closes. It joins the same busy authority as conversion and library generation, so each of the three holds the others off and every surface offering one reads a single answer.

The write takes one pass, or two where the user asks for a normalized peak. The first pass spills raw samples and discovers the peak, and the second reads them back and encodes at the scale that peak sets. Each pass names itself, so the bar crosses one axis, samples, twice, and holds a single unit across both. A cancel is honored between rows and between encoded blocks. A render that is stopped or fails clears the destination and the spill, so a path in a result always names a finished file.

## Teardown

The application stops every sound early in its teardown and closes the output last, before the interface goes. Closing ends every playback for good and declines every later claim. It then waits up to `AUDIO_TEARDOWN_SECONDS` for every audio thread: each writer, and each thread a source started through the output's registry, such as the song's renderer. A thread that outlives the deadline is reported.

The backend is terminated once every writer has ended. A writer still inside a device call keeps the backend running, since terminating it would reclaim memory that call still uses. The closing thread then ends that writer's playbacks itself, so every owner hears its end.

## Who governs what

| Concern | Owner |
|---------|-------|
| The devices the backend lists, and the device, rate and buffer size the reader chose | `DeviceCatalog` and `AudioDeviceManager` (`sampletones_core/audio/`) |
| The audio backend: the devices it lists and the streams it opens | `AudioDriverProtocol` and `PyAudioDriver` (`sampletones_core/audio/driver/`) |
| The one output every sound plays through: its claims, its stream, its writer and its threads | `AudioOutput` (`sampletones_core/audio/output/`) |
| One sound as its owner holds it, and what the owner hears of it | `Playback` and `PlaybackListener` (`sampletones_core/audio/output/playback/`) |
| Every decision the output makes, as state machines a model check covers | `SessionCore` (`sampletones_core/audio/output/session/`) and the lifecycles (`sampletones_core/audio/output/lifecycle/`) |
| Document audio played at the stream's rate | `BufferSource` (`sampletones_core/audio/output/buffer/`) |
| The song rendered ahead of the device, and its playback | `SongSource` and `SongPlayerService` (`services/song_player/`) |
| Every preview, and the one stop that reaches them | `PreviewPlayer` (`logic/shared/preview_player.py`) |
| The ranking that settles a contest for the device | `PlaybackPriority` (`logic/shared/`) |
| The verbs, target resolution, and the registry of sources | `coordinators/playback/` |
| A source's engagement reporting | the transport's player protocol, implemented per source |
| What the reader is told when a sound fails | `PlaybackFailurePresenter` (`coordinators/playback/failures.py`) |
| The boundary that hands a transport command's failure to the presenter | `GuardedPlayer` (`coordinators/playback/guard.py`) |
| The sequencer's mute set, its mask, and solo | `SequencerChannelsLogic` (`logic/sequencer/channels.py`) |
| A whole document's preview, read from the render cache or rendered on a worker of its own | `DocumentPreviews` (`logic/shared/previews.py`) |
| Row mixing, and the mask it pulls while rendering | `RowSynthesizer` (`logic/sequencer/playback/synthesizer/`) |
| A voice sounded on its own from a key, and its velocity's level | `LiveNote` and `velocity_level` (`sampletones_core/performance/`) |
| The keys played live, their one playback, and the pedal's state | `LiveKeysLogic` (`logic/shared/live/keys.py`) |
| Which press sounds, and whether a lift ends its note | `HeldKeys` and `release_ends_note` (`logic/shared/live/`) |
| A strike synthesized on a tick grid of its own, and the keys' linger | `SoundingNote` and `LiveNoteSource` (`logic/shared/live/`) |
| The generators at the rates in force, and the synthesis of one tick | `ChannelBank` and `synthesize_tick` (`logic/shared/synthesis/`) |
| The values a note starts from and a channel holds between frames | `ChannelPerformance` (`sampletones_core/performance/state.py`) |
| What a row's voice and pitch start, and what they move | `apply_row` and `note_step` (`sampletones_core/performance/rows.py`) |
| The face a pitch cell holds and the step it asks for | `Note`, `Step` and `step_of` (`sampletones_core/project/patterns/pitch.py`) |
| How a row's level and transpose reach what a channel sounds | `apply_modifiers` (`sampletones_core/performance/modifiers.py`) |
| How long a row lasts, and how many samples its ticks span | `SongTiming` and `TickClock` (`sampletones_core/timing/`) |
| Rendering the song to a file, its passes and its progress | `SongRenderService` (`services/render/`) |

The sequencer song is an ordinary intentional source alongside the reconstruction and instruction players. It implements the same protocol and is arbitrated by the same rules.
