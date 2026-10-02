# Screen Scenarios

This document governs the screen tier: tests that run the whole application, draw its frames on a display,
and press its controls the way a user does. It covers `tests/screens/`, where the scenarios live, and
`tests/suite/screens/`, which drives them. Consult it before writing a scenario, and when a change to the
interface needs proving that no lower tier can give.

---

## Principles

### 1. A behavior is proven at the lowest tier that sees it

Most behavior is proven below this tier. Logic is tested without DearPyGui, a widget on a real context
with simulated frames, and the whole application headless with its display calls stood in for. None of
them draws a frame. A screen scenario covers what only a drawn frame shows: where a control stands and
whether it fits, what a frame-lag contract decides, which scope a real key press reaches, hover, drag and
double-click, the exit and its teardown, and what a restart restores. A rule a screen depends on gets its
own case below, and the scenario keeps only what the screen adds.

### 2. A scenario drives the application a user runs

A scenario starts the application as `sampletones open` does and runs its own render loop unchanged. The
pointer and the keyboard are real input sent to the display, so a press travels the path a user's press
travels. A scenario reads what the screen shows and what the application wrote to disk. It reaches the
application through what the application makes public: tags, language keys, shortcuts, services and the
modal queue's snapshot. A seam a scenario needs and cannot find is added to the application as a public
one, which keeps the scenario independent of how the code is arranged inside.

### 3. Each scenario runs in a world of its own

Every scenario runs in a fresh process started in a home directory of its own, so settings, session state
and the documents folder hold only what the scenario put there. The process ends with the scenario, so the
exit and its teardown are part of what the scenario proves, and a crash on the way out fails it. A worker
draws on an X server of its own, so its scenarios take only its own input.

The `world` fixture says what the home holds before the first frame: the session a previous run left, the
settings, and the recordings, documents and libraries the scenario works on. Each file is written by the
model and the manager the application reads it with, so a seeded home is one a real run could have left. A
scenario class overrides `world` to seed its own. The [compatibility corpus](../../../tests/data/compatibility/README.md)
supplies the documents a release wrote, whole or damaged: restated at a version no step reaches, cut
short, or replaced by bytes of another kind.

### 4. A scenario is written to break the application

A scenario that only confirms the path its author had in mind proves little. Each rule a scenario proves
gets a positive example and a negative or boundary one, with real values, and each area is attacked along
the [questions](#questions-a-gui-change-asks) below.

- **A negative ends with its witness.** After the gesture that should change nothing, the same path is used
  once more where it should act, and then the whole state is asserted: the count is one lower and the row
  that left is the one named. A late effect of the negative then shows in the count. Waiting a fixed
  window instead would only restate the application's own delays.
- **A gesture confirms that it arrived** (see [Gestures](#gestures)), so a negative never passes because
  its input was lost.
- **A frame-lag promise is read on every frame** between the gestures, since a reading once a frame until
  it holds misses a flash that lasts one frame.
- **Where several states meet several doors, one suite walks the table**: every document state against
  every door that closes it, every kind of broken file against every door that opens one.
- **An expected value comes from the rule**: a language key with its arguments, a palette token, or a hand
  computation written in the test. A value the code under test answered proves nothing about that code.
- **A scenario that could pass vacuously is shown failing** on a fault planted for the purpose: a negative,
  an attack, or a check that reads state the gesture might never reach.

A break of something a document or a docstring states is recorded as a known bug, below, and its fix is
separate work. A break of behavior nothing states is a question for the maintainer.

### 5. A scenario waits for what it expects

Waiting is for a reading to hold. An expectation reads once a frame until it holds or its time runs out,
and a gesture waits for its control to be reachable and to stand still. A fixed sleep hides a race, and a
retry hides a bug: a scenario that passes only sometimes is a bug. A count of frames appears in a scenario
only where the count is the contract itself.

### 6. Every scenario is held to the same promises

Every scenario is held to the same after-checks. A failing gesture is logged and swallowed so the interface
keeps running, which is why the checks read the log as well as the screen.

- **Quiet.** The application logged no error and no thread let an exception escape. A scenario that
  provokes a failure claims the error it provokes, and an error nobody claims still fails it.
- **Contained.** The application started no program, and every file dialog it opened had an answer
  waiting.
- **Settled.** No modal conversation is left open, and every window lies inside the viewport.
- **Leaving cleanly.** The application leaves through the Exit shortcut without asking anything, stops,
  and writes its session state. Its background work winds down within the exit's deadline, and no thread
  of its own outlives the exit.

A known bug is a case marked `xfail(strict=True)` that names its [ledger](../bugs-and-todos.md) entry. The
mark makes the run fail once the bug is fixed, until the mark goes.

### 7. The DearPyGui layer knows nothing of SampleToNES

`tests/suite/screens/dearpygui/` drives any DearPyGui application: the process per scenario, the display,
the input, the readings and the waiting. The SampleToNES layer around it holds what belongs to this
application: the views, the stand-ins at its boundaries and the after-checks. A case in
`tests/integration/tooling/` holds the direction. The DearPyGui layer grows only when a scenario here needs
something, and it moves to a project of its own the day a second application wants it.

## How a scenario runs

The parent pytest run starts each scenario as a child pytest run of that one test, in a fresh interpreter.
The child writes its reports as it goes, and the parent reports them as its own, so selecting, rerunning and
strict expected failures behave as for any test. A child that crashes or runs out of time is reported as a
failure carrying its output.

Inside the child, the application is built on the main thread, where its render loop runs. The scenario
runs on a thread of its own. Every reading and every gesture crosses to the render thread through the
queue the application's own workers post to, between two frames ([the render thread](render-thread.md)).

## Gestures

A pointer gesture aims at the middle of a control once the control is in reach: it exists, it and every
container around it are shown, it was drawn in the last frame, it and every container around it answer a
press, its box lies inside the viewport, its middle lies in the part the regions around it leave in view, and
no modal window of another tree holds the screen. The control must also stand where it stood a frame before,
since a dialog sized by its content settles its place over its first frames ([dialogs](dialogs.md)).

A control in a region that scrolls is brought into view the way a person brings it: the wheel turns over a
region that takes the wheel, and the grip of a region's scrollbar is dragged where the region ignores the
wheel.

Keys are pressed on the real keyboard, with modifiers held a frame before the key. A scenario names an
action by its `ShortcutId`, and the keys come from the scheme in place. The display repeats no held key,
so a key held across a slow frame arrives as one press.

A gesture confirms that it arrived. Before a button goes down, the control must report the pointer resting
on it: DearPyGui calls a control visible while the region it scrolls in clips it, and a press there lands
on something else. While a button or a named key is held, the application must read it as down. A press
lost on the way fails where it was lost.

DearPyGui reports a position alone for a menu entry, so choosing one runs its callback the way a click does,
through the queue's own error reporting.

## Views

A scenario speaks through views, one per tab, card and dialog, under `tests/suite/screens/views/`. A view
knows its controls by their tags and its words by their language keys. A tag that moves changes one view,
and a scenario reads as the gestures a user makes.

## The boundaries

- **File dialogs.** A native dialog stops the queue while it stands, so a scenario queues its answer before
  the gesture that opens the dialog, and the stand-in answers at once.
- **Audio.** The default output device plays into silence in real time, so playback runs and nothing is
  heard. A scenario can start on a machine offering no device at all.
- **Programs.** An audit hook refuses every program the application tries to start: a file manager, a
  browser or a dialog tool would open on the desktop around the run. A shared library lookup passes.
- **The window manager.** The scenario's X server runs none, so `screen.close_window()` sends the request
  a title bar's close button sends.

## Holding work in flight

A gesture made while work runs is only proven if the work is provably still running when the gesture
lands. A hold keeps it there: a stand-in decides **when** the work lands and never **what** it computes.
A held conversion walks the stages a real one reports and stops halfway through matching, and a held
folder scan meets the folder's entries and then one entry after another that is no recording. Each goes
on reporting while it is held, so Stop and Cancel are heard where the real work hears them. A hold lasts
until the scenario releases it, and every hold is released before the scenario leaves, because leaving
waits for the work in flight. A scenario asks for a hold through its fixture, `conversion_hold` or
`scan_hold`.

## What survives a restart

What a restart keeps is proven in two halves, each a scenario on a fresh home. In the first, the application
leaves, and the scenario reads the files it wrote through their models. In the second, the world seeds the
same value through the same model, and the scenario reads it on the screen. A writer and a reader that
disagree fail one of the halves.

## Questions a GUI change asks

Before a change to the interface gets its scenarios, ask which of these it meets, and provoke it in a
scenario:

- **Render thread.** What does it touch in DearPyGui away from the render thread?
- **Teardown.** What happens when the window closes while it runs?
- **Modal over modal.** What if its dialog opens while another stands, waits or answers?
- **Frame lag.** Which geometry does it read in the frame that changes it?
- **In flight.** What if the user acts while its work is still running?
- **Unsaved work.** What does every path that replaces or closes a document ask?
- **Twice.** What does the same gesture do twice, and a double click against a single one?
- **Key scope.** Which scope claims its keys: a field, a modal, a panel, a collapsed card or a rebound key?
- **Palette.** Does a live palette swap repaint it?
- **Restart.** What of it survives a restart?
- **Scale.** Does it still answer with a large folder or a long list in it?
- **Failure.** What does the user read when a file is missing, old or truncated, or a write fails?

The list holds questions, never history. A fixed bug becomes a scenario, a step, a stand-in or an
after-check, and the list keeps only the general question that leads to it. A question joins only when no
question here would have led to the test that caught a bug, and near-duplicates merge, so the list stays
short enough to read before every change.

A bug fix's scenario is shown failing on the code before the fix, and the pull request says so.

## Running and watching

`make screens` runs every scenario across a few workers, each on an Xvfb of its own. `make system-deps`
installs Xvfb with the other development packages on Linux, and a missing server is named when the run
starts. The scenarios run on Linux, and [the ledger](../bugs-and-todos.md) holds the other platforms.

To follow a scenario as it plays, draw on Xephyr, which opens its screen as a window on the desktop:

```
SAMPLETONES_SCREENS_DISPLAY=xephyr uv run python -m pytest tests/screens --no-cov -k display_settings
```

Each scenario keeps its files under `build/screens/`, in a folder named after the test: the home the
application lived in, and a screenshot of the last frame when the scenario failed. `screen.capture` keeps a
picture as evidence of a look, for a pull request rather than an assertion.

## Who governs what

| Concern | Owner |
|---|---|
| A scenario per process, its reports | `tests/suite/screens/dearpygui/isolation.py`, `plugin.py` |
| The render thread crossing and waiting | `tests/suite/screens/dearpygui/bridge.py` |
| What a user can reach, and the gestures | `tests/suite/screens/dearpygui/reach.py`, `hand.py`, `semantic.py` |
| The display a worker draws on | `tests/suite/screens/dearpygui/display.py` |
| The application under test and how it ends | `tests/suite/screens/application.py` |
| The stand-ins at the boundaries | `tests/suite/screens/boundaries/` |
| Work held in flight | `tests/suite/screens/holds.py` |
| The after-checks | `tests/suite/screens/checks.py` |
| What a scenario holds and reads | `tests/suite/screens/screen.py`, `views/`, `steps/` |
| What a scenario's home holds | `tests/suite/screens/world.py` |
| The window manager's requests | `tests/suite/screens/dearpygui/windows.py` |
