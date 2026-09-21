# The Render Thread and What Crosses to It

This document describes how work reaches DearPyGui from somewhere other than the thread that owns
its context, and what each crossing costs. It governs `utils/gui/render_thread.py`,
`utils/gui/callbacks.py`, `utils/gui/frame.py`, and the queue in `utils/callbacks/`. Consult it when
a worker thread has something to show, when a gesture rebuilds widgets, when work needs a frame to
have been drawn first, or when work should run after a delay.

The design truth it realizes is principle 6 of [`architecture.md`](../architecture.md): DearPyGui's
context belongs to the render thread. This document holds the mechanism.

---

## A background result crosses through `CallbackQueue`

Services run long work on background threads and post each result to `CallbackQueue` with a priority. The
main-thread render loop **drains** the queue: each frame it runs the due results within a per-frame time
budget (`scheduling.queue_budget_seconds`), so a large backlog spreads across frames while rendering
continues. Every background result reaches UI state this way. Applying one to UI state directly from the
worker thread is forbidden.

A logic object hearing a worker's report, such as a library generation or the audio device's position,
posts its own handler to the queue the same way. The logic layer reaches the queue, and `utils/gui`
belongs to the visual layers.

## Work arriving from a worker crosses through `on_render_thread`

A thread of our own, such as a directory being read or a subtree being rebuilt, reaches the interface while
the render thread is walking the very items it would create and drop. An item freed there is freed with no
Python thread state, which crashes the process.

`on_render_thread` (`utils/gui/render_thread.py`) is the crossing. Work already on the render thread runs
where it stands, and work arriving from any other thread joins the queue. A worker that reads a value or
sets one on a standing widget still goes through it, since the hazard is the thread and not the gesture.

A run claims the drawing thread when its loop starts and lets it go when the loop stops. Where no run has
claimed the thread, as while the interface is being built, the work runs in place.

## A widget's own gesture is held for the frame

DearPyGui answers a gesture on a thread of its own, so a callback that rebuilds widgets there runs while
the render loop walks the very items it drops. `hold_callbacks` (`utils/gui/callbacks.py`) turns on manual
callback management when the context is created, and `run_held_callbacks` runs what DearPyGui gathered at
the top of each frame's drain. A gesture therefore reaches the interface from the thread that drew it, and
`on_render_thread` is a direct call inside a callback, because the callback already runs there.

What a gesture costs is paid between frames. A callback heavy enough to be felt should spread its work
across frames itself.

## A gesture that waits keeps the frames going

A callback on the render thread holds the frames up for as long as it runs, and a native dialog runs for as
long as the reader takes to answer it. `answered_while_drawing` (`utils/gui/render_thread.py`) puts that
waiting on a thread of its own and draws frames until it reports back. `utils/file_dialogs/api.py` opens
native dialogs this way. The gestures those frames gather wait for the drain that follows, so the interface
stays painted while it is inert.

## Work that needs a drawn frame names the frame it waits for

Reading a laid-out size, or letting a configuration take effect, needs a frame to have been drawn with it.
The drain runs between frames and not inside one. `FrameCallbackManager.set_frame_callback`
(`utils/gui/frame.py`) names the frame the work is picked up on, and a callback uses it to wait for one.

Work that needs a particular item drawn waits on that item instead. An item visible handler reports each
frame DearPyGui draws the item in and no frame it is hidden in, such as a collapsed card or a tab in the
back. Standing the handler on and off makes it the clock of work that follows the item on screen. The stems
list settles its windowed region this way.

The drain makes the wait a scheduled one. The render thread inside a drain is between frames, so the next
frame is the drain's own to reach. `dpg.split_frame` there waits for the very frame the wait itself
prevents, and the application stops for good. Naming a frame count with `set_frame_callback` asks for the
same wait and lets the loop keep running.

## Delayed work goes through the queue

To change the interface after a delay, post the change with `call_after` (`utils/callbacks/delay.py`). The
change waits in the queue until the delay has passed, and then runs on the render thread.

Work still waiting in the queue at shutdown is discarded, so delayed work never reaches the interface after
the context has closed. A separate timer thread could make such an access and crash.
