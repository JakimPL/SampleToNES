# Dialogs

A dialog sets its size once, and where it opens follows from that size. Consult this when a dialog opens at
the wrong size or in the wrong place, when a prompt raised from an answer never shows, and when adding one.
`GUIWindow` is the single place a dialog's window is opened, so what this document says holds for every
dialog the application raises.

## What a dialog sets

`DialogGeometry` (`layout/primitives.py`) carries a dialog's whole geometry:

- **`width`** is always set and is held both ways: it is the least the window may take and the most. A
  stretched item (a field, a combo, a button at `width=-1`) measures itself against the region the window
  offers. A window free to widen to its content, with content sized from the window, hands each other a
  little more every frame until the screen stops them. Holding the width at what the dialog sets leaves the
  two agreeing from the first frame. It also gives every dialog the same reading width whatever it holds.
- **`height`** is the size the dialog opens at. A dialog holding more than that grows to hold it, so a
  reader is always shown the whole of what the dialog says. A dialog that learns its length as it opens,
  such as a prompt whose text wraps or a form that unfolds a group once a run begins, leaves the height out
  and takes the height its content asks for.

Both must be above zero, so a position can always be computed from a dialog's size.

## Where a dialog opens

Every dialog opens centered on the viewport's client area, which is the space a position is measured in.

A dialog with a height is placed before it is ever drawn. Both numbers are in hand, so `GUIWindow.show` sets
the position between building the tree and the first frame that carries it. DearPyGui leaves an unplaced
modal where the pointer last was, and a position set through the API takes precedence over that. A placed
dialog therefore never appears at the pointer.

A dialog whose height its content settles has nothing to place from until a frame has measured it, so the
correction centers it. It is drawn once where the modal opened, once centered against the height it had
reached by then, and it stands where it belongs from the third frame on.

The correction re-reads the drawn size each frame and centers the window against it, so a dialog stays
centered all the way to the size it settles at. The correction ends once two readings agree. It ends on
purpose: a dialog has no `no_move`, so a reader can drag it, and a pass that kept measuring would drag it
back. The one window that changes size while it stands is the error dialog, whose **Show traceback**
unfolds a text box beneath the message. The correction has ended by then, so the dialog grows downward from
where it stands.

Each axis is held at zero at the least, so a dialog taller than the viewport keeps its title bar reachable.

## One modal at a time

DearPyGui shows one modal at a time. A modal built while another stands opens hidden, where nobody can
reach it, and its title-bar close runs as though the reader had dismissed it. A modal built in the frame
another one left in meets the same fate, since that frame still draws the one that left.

The screen therefore belongs to one conversation at a time. A conversation is a dialog, the modals it
hands the screen to while it steps aside, and the ones its answers raise. A modal asked for from anywhere
else, such as the report of a job that finished, waits in line. It opens once the conversation holding the
screen has ended, a frame after its last window left, and the line opens in the order it was asked. A dialog
asked for again while it waits keeps its place with the newer request, and one hidden while it waits leaves
the line.

**A question reads what it asks about once the screen is free for it.** A guard with something to ask
takes a turn in the line, and reads its state again when the line reaches that turn. The conversation that
held the screen has settled what it changes by then. An exit asked for while Close project asks therefore
finds the project Discard closed, and asks nothing about it. A guard with nothing to ask lets the request
through at once, whatever holds the screen, so closing the window over a dialog leaves at once when nothing
is unsaved. A turn that opens no question lets the line go on to the next window in the same frame.

`ModalQueue` (`utils/gui/modal_queue.py`) keeps the line. `GUIWindow.show` is the only way a window enters
it. A guard takes its turn through the `when_free` of the `DialogsRenderer` it was given, which `asking`
(`utils/callbacks/gates.py`) waits on. A caller raises a dialog whenever it has one to raise and never waits
a frame of its own for the screen. A window that reports work under way and leaves the rest of the interface
live beside it is no modal, so it opens at once.

## How a dialog answers

A dialog that closes on its answer leaves the screen first, and the answer runs a frame later as a hand-off
of its conversation. Whatever the answer raises, such as a question of its own or an error, opens ahead of
the line. Leaving also releases the dialog's keyboard claim, so a prompt the answer raises holds the
keyboard alone. `GUIWindow._leave_then` is that step. An answer that fails with an error leaves the hand-offs
after it, and the line, to go on a frame later.

What the answer needs, such as a ticked box or the fields of a form, is read before the dialog leaves. Only
the first answer runs: a second click reaches a dialog that has already gone.

The save prompt's Save runs the save once the prompt has gone, and the save reports a `SaveOutcome`. A
document written to disk goes on to what the prompt was guarding. A save the reader called off, such as a
file dialog closed without a name, brings the prompt back with the same question. A save that failed has
shown its error, and that error stands alone on screen. A save the prompt asked for shows no message of its
own when it lands, since the reader asked to go on and what the prompt guards opens next. A document with
no file to write to asks for one, the way Save As does.

A dialog that comes back once the modal it raised is answered steps aside. `yield_to` takes it off screen
and keeps its tree, and `resume` brings it back, a frame each way. The dialog keeps the screen while it
stands aside, so nothing waiting in line opens between it and the prompt it raised.

## A gesture asks once

A gesture that asks before it replaces a document, closes one or leaves the application holds one
conversation at a time. The conversation is the chain of questions the gesture passes, and every way out of
a question reaches whoever asked it. An answer that goes on lets the request through. Cancel, Escape, the
title bar's close and a save that failed turn it away. So does an error raised anywhere along the chain:
before a question, as the question reaches the screen, or after its answer. A request therefore always ends
in one of the two.

While a conversation stands, the same gesture asked for again asks nothing, so two closes before the first is
answered ask once. Once the conversation has ended, the gesture asks again. The span covers the wait for the
edits of the open reconstruction and the turn in the line too. A gesture repeated while an edit is on its way
asks once the edit lands, and one repeated while another conversation holds the screen asks once it ends.
`SingleFlight` (`utils/callbacks/gates.py`) holds the conversation, and the composition root wraps every such
gesture in one, whichever door it is asked for through.

**The latest request wins.** A gesture whose question is the same whatever it carries goes on with the
request made last. Starting or opening a document, editing a voice, closing and leaving ask this way. A
reader who double-clicks one file and then another before the question shows opens the second. The menu's
Open, asked for after a browser's file, shows the file dialog. Cancel drops every request the conversation
gathered. `LatestRequestFlight` holds such a conversation.

**A question built from the request keeps its request.** Loading what a run wrote asks whether the open
document is backed by that very file, so the answer holds for that file alone. A press made while the question
stands is absorbed, and the answer loads the file the question named. `FirstRequestFlight` holds such a
conversation.

## Where it is written

`GUIWindow.dialog_window` (`ui/elements/window.py`) is the only place a dialog's `dpg.window` is opened.
Every dialog is therefore modal, resists resizing and collapse, and offers the title bar's close button
exactly where it answers for closing. `GUIDialogWindow` adds the keyboard ring over it. The windows under
`utils/gui/dialogs/windows/` are the shapes the application raises without writing a window of its own: a
confirmation, a save prompt, an error report and a notice. A dialog that belongs to one tab lives under
`ui/panels/dialogs/`.

`centered_position` (`utils/placement.py`) is the arithmetic, and `viewport_center` and
`center_when_settled` (`utils/gui/align.py`) are the readings. `FrameCallbackManager` carries the frame the
correction waits on. [render-thread.md](render-thread.md) says why it counts frames and does not wait on
one.

Who *raises* a dialog is a different question, and [architecture.md](../architecture.md) answers it: dialog
presentation belongs to coordinators.
