# Stems in the application

This document covers what the application does with a reconstruction built from several stems: how it loads and names the recorded stems, what the Stems card offers, and what an edit or a removal does to the per-frame record. Consult it when changing an edit path, the record, or what the card offers.

The assignment that writes the record is [Stems reconstruction](../../concepts/stems.md). [Architecture](../architecture.md) describes the layers this code sits in.

Five terms recur. The **record** is the per-frame account of which recording plays each frame of each channel. A frame's **owner** is the recording the record names for it. A frame **rests** when nobody holds it, and the record then names the resting stem id. An **authored** frame is one the reader wrote by hand, and the record names the authored stem id. A **level** is a rank in the hierarchy the conversion used.

## The recorded stems

A stems reconstruction records one source per entry, naming its recording and the file it was read from. The application reads the locations through `Reconstruction.audio_filepath`, which `StemsData.paths` answers: a tuple holding one path per recording, and empty once the reconstruction is detached from its origin, as a project sample is. The names stay whatever happens to the locations, so a detached document still says which recordings it was built from. A document whose own file is removed in the Browser keeps the locations of its recordings.

Opening the document loads the recorded stems through `load_recordings`, at the scale the conversion recorded for the whole set it read. Each stem therefore carries the level it held in the conversion's mix, a stem heard on its own sounds at that level, and it keeps that level once another recording leaves the document. A document written before the scale was recorded holds one recording, which reads at its own peak, as its conversion read it. The mix of them is the original audio the source toggle and the waveform offer, computed fresh on every load. A recorded stem that is absent or unreadable on this machine follows the single-source rule: the whole original is unavailable, the approximation stands on its own, and the application names the first missing path in its dialog.

A document on disk is named after its file. The converter names that file from every recording it read, through the naming rules in `sampletones_core.reconstructions.naming`, so the name stands when a recording later leaves the document. A document held in memory, such as a project sample, carries the name it was given.

The Stems card names every recorded path, one row per stem. Each row has its own full-path tooltip and reveals its recording on a double-click. The Audio source panel keeps the reconstruction's own file, the choice between the two waveforms and the engine rate, which a document living on disk retimes as a step of its edits. A project sample leaves the rate to the project, and a document with no file keeps it until it is saved to one. The logic names which of the two locks the rate, and the panel's hint says that reason. Locating reveals every recorded path at once, in one window with every stem selected where the file manager supports that, and in one window per directory otherwise.

## The stems card

The reconstruction tab's Stems card turns the recorded assignment into a listener the user can steer. It draws the same list the converter's card draws: each row is one stem under the level it was picked on, named by its recording, with a leading master box and a colored box on every channel the stem holds frames on. A setup line above the rows names the assignment's hierarchy mode, and a **Collapse levels** toggle draws every row in one table where the banding is in the way. Ticking a box admits that stem's frames on that channel to everything the tab plays and exports, and unticking silences them.

### Principles of the card

1. **Selection filters what plays, shows what it filters, and scopes what is edited.** A ticked set projects the document and does not mutate it. The waveform shows the ticked frames alone. The reconstruction toggle plays them mixed, and original playback plays the recordings heard anywhere, mixed. The instruments panel draws the envelopes of that same part beside the figures measuring it, and both WAV export and instrument export write what stands on screen. Each answer derives from the recorded per-channel assignment, so a stem heard on one channel keeps its samples there and stays quiet on the next. The same set says which frames an instrument edit writes (see [Editing a stems reconstruction](#editing-a-stems-reconstruction)).

   Two rules shape the reading. **A filtered reading shows the frames it leaves out as silence in place**, so the envelopes, the waveform and the record line up column for column. **It ends at the last frame the reader hears**, so a channel whose sound the reader's choice took away reads as standing by: its plot is empty, its figures are at nothing and its instrument is written nowhere. A rest answers to no recording, so every reader hears it. A channel resting through every frame stands by in the document itself, whatever silenced it, so the figures beside a plot name the bytes the export writes. An edit that silences a channel is measured standing by as it arrives, and the panel draws that channel empty once its regeneration lands. Together these rules make what a reader sees, hears, edits and exports one and the same part of the document.
2. **A box appears where the choice reaches something.** A stem draws a box on a channel exactly where the record gives it a frame there, so every box the card offers changes what is heard. A recording holding no frame anywhere leaves the document, so every row offers a box somewhere. A document where no recording holds a frame keeps them all, and each of their rows reads as holding none. The frames a reader wrote by hand answer to no recording, so they gather in a row of their own that reads and behaves like any other.
3. **Every stem starts heard everywhere it holds frames.** A freshly opened stems reconstruction ticks every box, so the waveform and the original are the unfiltered document.
4. **The global channel choice takes precedence.** A channel switched off for the whole reconstruction mutes its column and leaves every value where the reader put it, so switching the channel back on restores the per-stem choice intact. The two compose by construction: the global choice filters the partials, and the stems choice filters the approximations.
5. **The selection follows the open document.** The card lives with the reconstruction it describes. Opening a document seeds the rows and the ticked boxes, a regenerated reconstruction keeps what the reader chose and ticks the channels a stem newly reaches, and closing the document empties the card.
6. **Listening choices stay out of the document.** The ticked set is session state, like every choice that shapes what is heard (see [Playback](playback.md)). Saving the reconstruction records the assignment and not the selection. The banding works the same way: collapsing the levels changes how the card draws and never what it describes.
7. **Removing a recording edits the document.** Where a box steers listening, the remove button rewrites what is described. The change is asked about first and recorded in the project history, and [Editing a stems reconstruction](#editing-a-stems-reconstruction) says what it releases. A reconstruction holds at least one recording, so the last row standing keeps its button disabled.
8. **The ribbon shows what the record holds.** Under the waveform, a lane per channel in play divides into the stretches one recording holds throughout, each painted in that recording's color. A recording takes its color from the id it was converted as, which it keeps for as long as it stays on the record. One recording therefore reads alike wherever it is drawn — on this card, under the waveform, beneath an instrument's bars, and in the list [the browser](browser.md) shows on hovering a reconstruction — and a recording leaving the document leaves the others' colors as they were. A lane appears for every channel in play, one unbroken stretch where a single owner holds it throughout, so a channel's lane answers whether it sounds and by whom independently of every other channel's. A stretch reads solid where the reader hears the recording holding it, faded where the reader left it out, and in the surface's own ground where the frames rest. It names its owner whether or not it is listened to. The instruments panel paints the same stretches in a band beneath each dimension's bars, where a dimension answering to a single owner has nothing to tell apart and draws no band.
9. **The menu makes the same choices as the boxes.** A right-click on a row offers Mute or Unmute, Solo or Unsolo, and the file items every listing offers. Mute and Unmute set the recording's choice across every channel it offers. Solo hears one recording on every channel it offers and silences the others, and it remembers the choice it replaced, so Unsolo returns to it whichever recordings were soloed in between. A choice made by hand, or a regenerated document, ends that memory, and Unsolo then hears every recording whole. The frames a reader wrote have no file, so their row offers no file items. Both choices stay session state, like the boxes.

### What the code guarantees

A filtered mix keeps every array at its unfiltered length, so it aligns with the unfiltered one sample for sample. The filter zeroes the unselected frames per channel before mixing (`filter_approximations`), and the original mix covers the recordings of the stems heard on any channel. It is silence while no stem is heard, and there is none while no recording loaded. The panel logic holds the channels each stem is heard on and re-answers the stems view model, the waveform and the audio data whenever the choice changes. A reconstruction that records one source presents a single row for its recording, and one that records no source shows the card's empty state.

Removal runs through `without_stem`, which returns a fresh reconstruction holding what the rules in [Editing a stems reconstruction](#editing-a-stems-reconstruction) leave. A confirmed removal is a step of the open document's edits, taken after the edits made before it ([Editing the open reconstruction](reconstruction-edits.md)), and it lands as a `ReconstructionEdit`, the payload both a regenerated instrument and a removed recording travel as. One path therefore rebinds the open document and records the edit against the project history. They differ in what the instruments panel does. A regenerated instrument carries the envelopes the panel's own edit wrote, so the panel keeps drawing them. A removal redraws every channel from the document it leaves.

## Editing a stems reconstruction

A conversion answers, per channel and frame, which recording plays there. Everything a reader does to the document afterward stands on that answer: the instruments panel rewrites what a channel plays, the stems card chooses what is heard, and the remove button takes a recording out. This section describes the account of ownership all three keep, and the rules each gesture follows.

### Principles of editing

1. **A frame has exactly one owner.** Every frame of a channel in play is held by one recording, by the reader's own hand, or by nobody. The hardware reads one instruction per channel per frame, so the channel itself allows only this, and it makes the per-frame record a partition of the channel's frames. The resting stem id names the frames nobody holds, and the authored stem id names the frames the reader wrote.
2. **Rest and silence name the same frames.** A frame rests exactly when its instruction is silent, which the conversion establishes and every later gesture keeps. A reader looking at a silent frame and a reader looking at the record therefore learn the same thing, and the rules below follow from it.
3. **An edit rewrites what a frame plays and leaves who plays it.** Ownership answers a question an edit does not ask, so a frame carries its owner through any change to its instruction. A frame takes an owner by coming into play and releases it by falling silent. A reader can therefore shape a recording's part while the document keeps its account of where that part came from.
4. **A reconstruction records what is played and reads what is heard.** The document holds the instruction each channel plays per frame, the recording behind each of those frames, the setup they were chosen under and the working level. Its sound is read from those through the generators, as the instructions stand. That one answer serves the waveform, playback, an export and the mixed approximation alike. A drive settles which instruction a conversion records and is read no further. Every gesture below is therefore complete once it has settled the frames.
5. **What is heard is what is edited.** The channels a recording is ticked on are one choice serving two readings: the frames the waveform draws, and the frames an edit writes. A recording switched off on a channel reads there and stays as it stands, so a reader reaches one recording's part at a time through the card already in front of them.
6. **The setup is the conversion's, and a recording leaving is what rewrites it.** The entries, the levels, the channels each recording may occupy, its bends, its drives and its count record how the document was made. A gesture leaves them as they stand for every recording still holding a frame. A recording leaves the setup when a removal takes it out, or when an edit leaves it holding no frame, and it takes its source and its place in the hierarchy with it.
7. **Detaching drops where a recording lives and keeps who played what.** A recording's name and the frames it holds belong to the document, and its location belongs to this machine. The record keeps both, so detaching lets each location go and keeps every name. A reconstruction embedded in a project therefore keeps a working stems card.

### What the record holds

The per-frame record answers for every channel in play, and these hold after every gesture:

- A channel in play sounds in some frame, and has one owner per frame of its stream, each naming a recorded entry, the resting stem id or the authored stem id.
- A channel resting through every frame stands by, whatever silenced it, and has no stream and no record at all.
- A frame rests exactly where its instruction is silent.
- A frame a recording holds lies on a channel that recording's settings occupy, and an authored frame answers to no settings.
- Every entry holds a frame somewhere, unless no entry does. A recording left holding no frame leaves the record, while a record where none holds a frame keeps them all, since nothing sounds that could tell them apart.

### What an edit carries

An edit hands one channel a fresh set of envelopes, which become that channel's stream. Each frame's owner follows from the frame it was and the frame it becomes:

| the frame | becomes |
|---|---|
| sounding before and after | its owner, unchanged |
| sounding, edited silent | resting |
| resting, edited into play | authored |
| resting, edited silent | resting |
| written past the end of the stream | authored where it sounds, resting where it stays silent |
| dropped from the end of the stream, within the scope | gone, together with its ownership |
| dropped from the end of the stream, outside it | standing, in what it plays and who plays it |

Rest and silence naming the same frames makes the table total. A frame's owner before the edit already says whether it sounded, so the first four lines cover every frame the edit keeps at its position.

An edit shortens a channel as far as its scope reaches. The stream therefore runs through the last frame standing outside that scope. The frames the edit did reach rest along the way. A stream edited down to no frame, or to rests alone, leaves its channel standing by, and the channel keeps the reference and the held dimensions the edit states. A channel written back into play comes back wholly authored. The identifier, the configuration and the working level stand throughout. The setup and the recorded sources stand for every recording still holding a frame, and a recording the edit leaves holding none leaves them, unless no recording holds a frame at all.

**The scope an edit writes in** follows principle 5: a frame accepts a gesture where its owner is ticked on that channel, and where it rests. The frames a reader wrote answer to a row of their own, so they are ticked and reached like any recording's. A rest belongs to no row, which lets a gesture write a note into silence. Every other frame draws dimmed and reads as it stands. The scope is the same selection the waveform filter reads, so one state answers both, and a reader narrowing what they hear narrows what they change with it.

### What a removal releases

Taking a recording out (`without_stem`) releases the frames it held. Each takes its channel's silent instruction and the resting stem id. A channel the removal leaves resting through every frame stands by, and keeps the reference and the held dimensions it was shaped with, as an edit keeps them. The entry and its source leave the record, and a level the removal empties collapses. The ids of the recordings that stay are left alone, so the record, a reader's selection and every recording's color all stay valid. A reconstruction holds at least one recording, so the last one standing keeps its place.

A frame that stays keeps the instruction it played and the recording that held it. Its samples follow from principle 4: a channel the removal reached is read afresh, so its oscillator runs through the silence the removal left and not through the notes it took away.

An edit made before the removal changes nothing about it: the channel carries its record whatever was written into it, so the frames the recording held are released the way they would have been. The frames the reader authored answer to no recording and stand through every removal.
