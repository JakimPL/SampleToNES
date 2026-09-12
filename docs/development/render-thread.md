# The Render Thread and What Crosses to It

This document describes how work reaches DearPyGui from somewhere other than the thread that owns
its context, and what each crossing costs. It governs `utils/gui/render_thread.py`,
`utils/gui/callbacks.py`, `utils/gui/frame.py`, and the queue in `utils/callbacks/`. Consult it when
a worker thread has something to show, when a gesture rebuilds widgets, or when work needs a frame
to have been drawn first.

The design truth it realizes is principle 6 of [`architecture.md`](architecture.md): DearPyGui's
context belongs to the render thread. This document holds the mechanism.

---

## A background result crosses through `CallbackQueue`

Services execute long-running work on background threads and post each result to `CallbackQueue`
with a priority; the main-thread render loop drains the due results each frame within a per-frame
time budget (`scheduling.queue_budget_seconds`), so a large backlog spreads across frames while
rendering continues. Every background result reaches UI state this way, and applying one to UI state
directly from the worker thread is forbidden.

## Work arriving from a worker crosses through `on_render_thread`

A thread of our own — a directory being read, a subtree being rebuilt — reaches the interface while
the render thread is walking the very items it would create and drop, and an item freed there is
freed with no Python thread state: a crash rather than a glitch.
`utils/gui/render_thread.py::on_render_thread` is that crossing: work already on the render thread
runs where it stands, and work arriving from any other thread joins the queue. A worker that reads a
value or sets one on a standing widget still goes through it, since the hazard is the thread rather
than the gesture.

A run claims the drawing thread when its loop starts and lets it go when the loop stops. An
unclaimed context runs the work in place, which is what an interface being built stands in.

## A widget's own gesture is held for the frame

DearPyGui answers a gesture on a thread of its own, so a callback that rebuilds widgets there runs
while the render loop walks the very items it drops. `utils/gui/callbacks.py::hold_callbacks` turns
on manual callback management when the context is created, and `run_held_callbacks` runs what
DearPyGui gathered at the top of each frame's drain. So a gesture reaches the interface from the
thread that drew it, and `on_render_thread` is a direct call inside a callback because the callback
already stands there.

## A gesture that waits keeps the frames going

A callback standing on the render thread holds the frames up for as long as it runs, and a native
dialog runs for as long as the reader takes to answer it.
`utils/gui/render_thread.py::answered_while_drawing` puts that waiting on a thread of its own and
draws frames until it reports back, which is how `utils/file_dialogs/api.py` opens one. The gestures
those frames gather wait for the drain that follows, so the interface stays painted while it stands
inert.

## Work that needs a drawn frame names the frame it waits for

Reading a laid-out size or letting a configuration take effect needs a frame to have been drawn with
it, while the drain runs between frames rather than inside one.
`FrameCallbackManager.set_frame_callback` (`utils/gui/frame.py`) names the frame the work is picked
up on, and is how a callback waits for one.

The drain is what makes the wait a scheduled one. The render thread inside a drain is between frames
rather than inside one, which makes the next frame the drain's own to reach, so `dpg.split_frame`
there waits for what the wait itself prevents and the application stops for good. Naming a frame
count asks for the same thing and lets the loop keep running.
