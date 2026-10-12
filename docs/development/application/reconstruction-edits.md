# Editing the Open Reconstruction

This document describes how the Reconstructions tab changes the document it has open. It governs
`logic/reconstruction/rewrites/` and the parts of `ReconstructionCoordinator` that put a document away or
wait on its edits. Consult it when adding a gesture that edits the open document, one that reads or puts
away the whole document, or one that replaces the document from outside the tab.

A rebuild of an edited channel, and the render of the audio it sounds, run on a worker thread, so the
reader can make the next change before the last one has landed and the frames keep coming while the
rebuild renders. The worker takes the renders the cache holds for the document with it and hands back the
audio of every channel in play, the mix of what the reader hears, and the envelopes each channel exports
for the recordings heard; the landing keeps the audio in the cache and installs the envelopes where the
instruments panel reads them before the tab reads either. A change to what is heard whose sound the
cache keeps none of is a step of the same line, rendered by the same worker. Every rule below keeps the
document as though each change had landed before the next one was made.

---

## One step at a time, in the reader's order

The open document changes as a line of steps: a channel the reader moved, a recording taken out, a new NES
frequency, and a gesture that reads or puts away the whole document. The line takes one step at a time, in
the order the reader asked for them, and each step is built from the document the step before it left. Two
quick edits therefore both land, whichever dimensions or channels they touch.

A step the line takes, or a result it lands, may ask for another step, as an undo redrawing the document
asks for a listening. The ask joins the line and is taken once the step or the landing has returned, so a
gesture never runs inside another one.

## A step carries what the reader moved

A channel change holds the dimensions the reader moved alone. At its turn it is written over the
envelopes the document holds then, and it reaches the recordings the reader hears then. The rest of the
channel is read afresh, so what a step before it rebuilt stands. A set of envelopes read from an older
document names every frame of the channel, a frame a removal has since released included, and writing it
back would make that frame the reader's own ([Stems in the application](stems.md)).

Changes of one channel waiting next to each other merge into one, so a drag collapses into the place it
ended. A change joins a change of its own channel waiting at the end of the line. The running rebuild and
every other step keep their places, so each position the reader asked for is rebuilt or overtaken by a later
one.

## A result lands on the document it was computed from

A rebuild remembers the document it started from, and its result lands only while that document is open. A
change from outside the tab that replaces the document, such as a load, opening another voice, a close, an
undo reaching the open sample or a replaced sample, puts away the edits meant for the document it replaces.
The result of a rebuild still running for it is dropped when it arrives. A closed or replaced document
therefore keeps what it held, and the history stays as it was.

## The panel draws what the document will hold

The instruments panel reads the document's envelopes through the changes still on their way, so the bars,
the plots and the byte figures answer for the document once the line empties. A change the line lets go of,
such as a failed rebuild, redraws the panel from the document as it stands.

A removal, a retune, an undo and a new choice of what is heard leave the envelopes to the worker. The panel
keeps the envelopes it drew until the next ones land, and it takes no edit of them meanwhile, since an edit
would be written against frames the reader no longer hears. A document just opened has none to keep, so the
panel says its instruments are being prepared.

## A step that no longer applies is skipped

A step meets the document the steps before it left. A removal of a recording an earlier step already took
out, or of the last recording standing, is skipped. So is a rate the document already runs at.

## A gesture on the whole document waits for the edits before it

Undo, redo and a history jump, saving, loading, opening a voice, closing, exporting, adding the document to
the sequencer, the project's own save, new, open, close, export and render, a new project rate, removing,
replacing or duplicating a voice, taking an instrument from it or exporting one, and the exit all read or
put away a whole document. Each waits for the edits made before it, so an undo right after a drag undoes the
drag and a save writes it. With nothing on its way, the gesture runs at once.

A channel change drawn while a removal or such a gesture waits is refused, since it was drawn on a view the
waiting step is about to change. The panel is redrawn once the line empties, which takes the refused change
off the screen.

## The project rate reaches the open sample as a step

A new project rate retunes the samples in the background, one batch for all of them. The rate waits for the
edits before it, and the sample open on the tab then takes it as a step of its own line, so the sample
joins the rate change's history entry with every other sample. A batch result for a sample edited since the
batch started is retuned again from what the sample now holds.

## A change to what is heard is a step

A box on the stems card or above the waveform changes the reader's listening. The stems card and the
ribbon answer at once. The waveform, the audio and the envelopes the instruments panel draws are read
from what the worker landed for the hearing. Where the screen holds none of it, the panel owes the showing
and asks for a listening step, which renders the hearing of the document as it then stands and lands like
a rebuild. The reader's choice travels onto a new record by one rule, written in core and read by the
worker and the listening state alike (`carried_hearing`), so the sound and envelopes a landing installs
are the ones the listening then reads. One listening waiting answers every choice made before it is
taken. A freshly opened document, a removal, a retune, an undo and a save-as are shown the same way,
their sound and envelopes landed by a listening. Every gesture that reads the sound joins what the panel
owes, so a flip of the source or a retune during a showing on its way settles with it. A WAV export is a
reading of what plays like a showing: it writes the kept sound at once, or waits beside the showing and
is written for what the reader hears once the sound lands. A document put away before that, or a reading
that fails, drops the export and tells the reader so. A channel change reaching its turn while the
envelopes of what is heard are on their way waits behind a listening of that choice.

## The line catches up with what is heard

A listening renders the choice standing when it starts, and the reader may move on before it lands. Its
envelopes are kept only where they still answer the reader's choice. Once the line stands idle after a step
or a landing, the open document holds the envelopes of what the reader hears, or the line asks the worker
for them. The panel and the waveform therefore settle on the reader's last choice once the reader stops.
A listening already running for the choice answers it, so no reading is rendered twice. A choice whose
listening failed is asked for again once the reader makes another.

## The waveform fades while the line is busy

The waveform is faded from the moment a step waits or runs until the last one lands, so a reader sees the
document is being rewritten for the whole span, however many steps it takes. The status bar names what
the fade waits for: `global.graph.message.waveform_regenerating` for an edit on its way, and
`global.graph.message.waveform_reading` for a change to what is heard or a document just opened. The line
reports the kind of work it is busy with, so a hand-over from an edit to a reading of the sound changes
the words under the same fade.
