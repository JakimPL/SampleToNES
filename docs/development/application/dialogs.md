# Dialogs

A dialog states its size once, and where it opens follows from what it states.
Consult this when a dialog opens at the wrong size or in the wrong place, and
when adding one: `GUIWindow` is the single place a dialog's window is opened, so
what this document says holds for every dialog the application raises.

## What a dialog states

`DialogGeometry` (`layout/primitives.py`) carries a dialog's whole geometry:

- **`width`** is stated always, and held both ways: it is the least the window
  may take and the most. A stretched item — a field, a combo, a button at
  `width=-1` — measures itself against the region the window offers, so a window
  free to widen to its content and content sized from the window hand each other
  a little more every frame until the screen stops them. Holding the width at
  what the dialog states leaves the two agreeing from the first frame, and gives
  every dialog the same reading width whatever it holds.
- **`height`** is the size the dialog opens at. A dialog holding more than that
  grows to hold it, so what a reader is shown is always the whole of what the
  dialog says. A dialog whose length it learns as it opens — a prompt whose text
  wraps, a form that unfolds a group once a run begins — leaves the height out
  and takes the height its content asks for.

Both are bounded above zero, so a dialog can never state a size a position
cannot be computed from.

## Where a dialog opens

Every dialog opens centered on the viewport's client area, which is the space a
position is measured in.

A dialog stating a height is placed before it is ever drawn: both numbers stand
in hand, so `GUIWindow.show` sets the position between building the tree and the
first frame that carries it. DearPyGui leaves an unplaced modal where the pointer
last was, and a position set through the API takes precedence over that, so a
placed dialog never appears at the pointer.

A dialog whose height its content settles has nothing to place from until a frame
has measured it, so it is centered by the correction instead. It is drawn once
where the modal opened, once centered against the height it had reached by then,
and stands where it belongs from the third frame on.

The correction re-reads the drawn size each frame and centers the window against
it, so a dialog stands centered the whole way to the size it settles at. It ends
once two readings agree, and ends deliberately: a dialog carries no `no_move`, so
a reader can drag it, and a pass that kept measuring would drag it back. The one
window that changes size while it stands is the error dialog, whose **Show
traceback** unfolds a text box beneath the message; the pass has ended by then,
so the dialog grows downward from where it stands.

Each axis is held at zero at the least, so a dialog taller than the viewport
keeps its title bar reachable.

## Where it is written

`GUIWindow.dialog_window` (`ui/elements/window.py`) is the only place a dialog's
`dpg.window` is opened, so every dialog is modal, resists resizing and collapse,
and offers the title bar's close button exactly where it answers for closing.
`GUIDialogWindow` adds the keyboard ring over it, and the four windows under
`utils/gui/dialogs/windows/` — a confirmation, a save prompt, an error report and
a notice — are the shapes the application raises without writing a window of its
own. A dialog that belongs to one tab lives under `ui/panels/dialogs/`.

`centered_position` (`utils/placement.py`) is the arithmetic, `viewport_center`
and `center_when_settled` (`utils/gui/align.py`) the readings, and the frame the
correction waits on is carried by `FrameCallbackManager` — see
[render-thread.md](render-thread.md) for why it counts frames rather than waiting
on one.

Who *raises* a dialog is a different question, and
[architecture.md](../architecture.md) answers it: dialog presentation belongs to
coordinators.
