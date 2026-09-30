# Editing the Open Reconstruction

This document describes how the Reconstructions tab changes the document it has open. It governs
`logic/reconstruction/rewrites/` and the parts of `ReconstructionCoordinator` that put a document away or
wait on its edits. Consult it when adding a gesture that edits the open document, one that reads or puts
away the whole document, or one that replaces the document from outside the tab.

A rebuild of an edited channel runs on a worker thread, so the reader can make the next change before the
last one has landed. Every rule below keeps the document as though each change had landed before the next
one was made.

---

## One step at a time, in the reader's order

The open document changes as a line of steps: a channel the reader moved, a recording taken out, a new NES
frequency, and a gesture that reads or puts away the whole document. The line takes one step at a time, in
the order the reader asked for them, and each step is built from the document the step before it left. Two
quick edits therefore both land, whichever dimensions or channels they touch.

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

## A step that no longer applies is skipped

A step meets the document the steps before it left. A removal of a recording an earlier step already took
out, or of the last recording standing, is skipped. So is a rate the document already runs at.

## A gesture on the whole document waits for the edits before it

Undo, redo and a history jump, saving, loading, opening a voice, closing, exporting, adding the document to
the sequencer, the project's own save, new, open and close, removing or replacing a voice, and the exit all
read or put away a whole document. Each waits for the edits made before it, so an undo right after a drag
undoes the drag and a save writes it. With nothing on its way, the gesture runs at once.

A channel change drawn while a removal or such a gesture waits is refused, since it was drawn on a view the
waiting step is about to change. The panel is redrawn once the line empties, which takes the refused change
off the screen.

## The project rate reaches the open sample as a step

A new project rate retunes the samples in the background, one batch for all of them. The sample open on the
tab takes the rate as a step of its own line, so it follows the edits made there and joins the rate change's
history entry. A batch result for a sample edited since the batch started is retuned again from what the
sample now holds.

## The waveform fades while the line is busy

The waveform is faded from the moment a step waits or runs until the last one lands. A reader sees the
document is being rewritten for the whole span, however many steps it takes.
