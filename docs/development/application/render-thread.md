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

A report of where a run stands crosses through `LatestDelivery` (`utils/callbacks/latest.py`). One delivery
waits in the queue at a time, and the drain that reaches it hands over the newest report filed, so a burst
of reports costs one handling. The delivery keeps the place its first report took, which keeps a result
posted after that report, such as the run's outcome, behind it. [Progress](../progress.md) gives the
principle.

A result carries what the landing installs. The regeneration worker renders every sound the
Reconstructions tab draws or plays: each channel's audio, the mix of what the reader hears, the mix of the
recordings heard, which the waveform draws as the original, and the envelopes each channel exports for the
recordings heard. It hands them back inside its result. The landing keeps the audio in the render cache
and installs the envelopes, on the render thread. A reading the cache leaves unanswered is asked of the
same worker and lands the same way. What a worker produces for the interface therefore reaches what the
interface reads through the queue alone, and the render thread computes no sample while the worker
renders. A document previewed elsewhere reads the same cache and asks a worker of its own for what the
cache lacks (`DocumentPreviews` in `logic/shared/previews.py`), and sounds at the landing; a
reconstruction file a browser tree plays is read from disk and previewed the same way. The render cache
keeps what the landings adopt, so its writers are the landings, every one of them on the render thread.

A logic object hearing a worker's report, such as a library generation, posts its own handler to the
queue the same way. The logic layer reaches the queue, and `utils/gui` belongs to the visual layers.

The audio output is built with the queue's `add` as the post every playback report takes. Its writer
thread posts each position and each end report there at one priority, so an owner hears its playback on
the render thread, in the order the output made the reports, with the end report last.

A failure crosses the same way. `UnhandledFailures` posts the report of a failure nothing recovered from to
the queue, so the error dialog is built on the render thread whichever thread failed (see the Error Handling
Policy in [`architecture.md`](../architecture.md#entry-points--the-last-resort)).

## Work arriving from a worker crosses through `on_render_thread`

A thread of our own, such as a subtree being rebuilt, reaches the interface while the render thread is
walking the very items it would create and drop. An item freed there is freed with no Python thread state,
which crashes the process.

`on_render_thread` (`utils/gui/render_thread.py`) is the crossing. Work already on the render thread runs
where it stands, and work arriving from any other thread joins the queue. A worker that reads a value or
sets one on a standing widget still goes through it, since the hazard is the thread and not the gesture.

A run claims the drawing thread when its loop starts. Where no run has claimed the thread, as while the
interface is being built, the work runs in place.

The thread that drew keeps the context after the loop stops, until the context is destroyed, since the
teardown runs there. A worker's work that arrives after the loop has stopped joins the queue like any
other, and nothing drains the queue once the loop has stopped, so that work never runs. The context being
taken down therefore stays with the thread taking it down. A worker reading something long, such as a folder, also listens for
the shutdown and gives up at its next step, so the teardown finds it ended.

## A widget's own gesture is held for the frame

DearPyGui answers a gesture on a thread of its own, so a callback that rebuilds widgets there runs while
the render loop walks the very items it drops. `hold_callbacks` (`utils/gui/callbacks.py`) turns on manual
callback management when the context is created, and `run_held_callbacks` runs what DearPyGui gathered at
the top of each frame's drain. A gesture therefore reaches the interface from the thread that drew it, and
`on_render_thread` is a direct call inside a callback, because the callback already runs there.

What a gesture costs is paid between frames. A callback heavy enough to be felt should spread its work
across frames itself.

**A held gesture reads the items still standing.** The callback runs after the frame that gathered it, and
a rebuild in between can take away the row a hover, a click or a drop landed on. A callback reads what that
item carries through `dpg_get_item_user_data` (`utils/gui/dpg.py`), which answers nothing for an item that
is gone, so a gesture on a row the list has dropped says and does nothing.

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
