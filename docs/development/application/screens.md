# Screen Scenarios

This document governs the screen tier: tests that run the whole application, draw its frames on a display,
and press its controls the way a user does. It covers `tests/screens/`, where the scenarios live,
`tests/suite/screens/`, which holds the material they seed their homes with, and `automation/`, the unit that
drives the application for them. Consult it before writing a scenario, and when a change to the interface
needs proving that no lower tier can give.

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
scenario class overrides `world` to seed its own, and a folder of scenarios working on the same documents
overrides it once in its `conftest.py`. The [compatibility corpus](../../../tests/data/compatibility/README.md)
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

A wait's time runs in seconds and in frames: the frames a machine drawing 30 a second draws in those
seconds. The wait ends once both have run, so a machine drawing slowly gives the application as many frames
as a fast one before an expectation fails. A witness that lasts a moment is read where it stays: a sound
counts once it reaches the output device, and a stopped read that must still be winding down is held there
until the scenario lets it go.

### 6. Every scenario is held to the same promises

Every scenario is held to the same after-checks. A failing gesture is reported and the interface keeps
running: the failure is logged, and the error dialog shows it unless a report already stands. The checks
therefore read the log as well as the screen.

- **Quiet.** The application logged no error and no thread let an exception escape. A scenario that
  provokes a failure claims the error it provokes, and an error nobody claims still fails it.
- **Contained.** The application started no program, and every file dialog it opened had an answer
  waiting.
- **Settled.** No modal conversation is left open, and every window lies inside the viewport.
- **Leaving cleanly.** The application leaves through the Exit shortcut without asking anything, stops,
  and writes its session state. Its background work winds down within the exit's deadline, and no thread
  of its own outlives the exit.

A known bug is a case marked `xfail(strict=True)` that names its [ledger](../bugs-and-todos.md) entry. The
mark makes the run fail once the bug is fixed, until the mark goes. A known crash is marked the same way:
the parent reports a marked scenario whose process a signal killed as the failure it expects, naming the
signal.

### 7. The driver is a unit of its own, and its DearPyGui layer knows nothing of SampleToNES

`automation/` operates the running application from outside, for whoever needs it driven: the scenarios
here, and the pictures the guide is illustrated with ([assets](../assets.md)). It stands beside the
source tree as a checkout unit ([tooling](../tooling.md)): it imports the program and nothing from
`tests/`, and the import-boundary check holds it to that. The scenarios' material stays in the test tree: the seeds and
the worlds built from the archived corpus, the mini library and the history projects are what the
scenarios prove with, so `tests/suite/screens/` keeps them and the plugin asks for a world by its fixture.

Inside the unit, `automation/dearpygui/` drives any DearPyGui application: the process per scenario, the
display, the input, the readings and the waiting. The SampleToNES layer around it holds what belongs to
this application: the views, the stand-ins at its boundaries and the after-checks. A case in
`tests/integration/tooling/` holds the direction. The DearPyGui layer grows only when a scenario here needs
something, and it moves to a project of its own the day a second application wants it.

## How a scenario runs

The parent pytest run starts each scenario as a child pytest run of that one test, in a fresh interpreter.
The child writes its reports as it goes, and the parent reports them as its own, so selecting, rerunning and
strict expected failures behave as for any test. A child that crashes or runs out of time is reported as a
failure carrying its output, unless a crash is the known bug its scenario is marked with.

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
wheel. The hand measures how far to scroll once a frame has laid the control out: a row found in the frame
that built it has no place yet, and a region learns how far it scrolls a frame after it draws what it
holds. A table that scrolls its own rows, such as the tracker's, is a region for those rows: its view
begins below the rows it freezes, and those stay in view whatever the scroll.

Keys are pressed on the real keyboard, with modifiers held a frame before the key. A scenario names an
action by its `ShortcutId`, and the keys come from the scheme in place. The display repeats no held key.

Dear ImGui judges a press by time: two presses count as a double-click when they land within 0.30 s, and a
key held past 0.275 s repeats. A click and a key press therefore go down and come up in one go, and Dear
ImGui reads the press on one frame and the release on the next at any frame rate. A key stands down for a
single frame, too briefly to repeat, and the presses of a double-click land two frames apart. Where two
frames take longer than the double-click time, the hand raises `SlowFramesError` and says how far apart the
presses landed.

A person lets go of a click some frames after pressing it, and DearPyGui answers a double-click as its
second press goes down. A scenario holding that press for as long as a person does sees what the answer
brings under a button still down.

A gesture confirms that it arrived. Before a button goes down, the control must report the pointer resting
on it: DearPyGui calls a control visible while the region it scrolls in clips it, and a press there lands
on something else. While a button or a modifier is held, the application must read it as down within a
few frames, since a busy display hands input on late. A click or a key press that came and went is
confirmed by a witness, a handler registry of the hand's own that counts every release and every
double-click Dear ImGui reads. Each step of a drag waits until the application reads the pointer where the
step put it, and the pointer rests at the end before the button comes up, as a person stops before letting
go. A press lost on the way fails where it was lost.

A worker's scenarios take its display in turn, and a key or a button left down would meet the next
scenario's first gesture. A gesture that fails lets go of what it holds, and each scenario starts and ends
with every key and button of the display up.

A plot reads the pointer as it draws, so the value it puts under the pointer trails the pointer by a
frame. A scenario that aims by plot values reads one once the plot has kept it for two frames in a row.

DearPyGui reports a position alone for a menu entry, so choosing one runs its callback the way a click does,
through the queue's own error reporting.

## Views

A scenario speaks through views, one per tab, card and dialog, under `automation/views/`. A view
knows its controls by their tags and its words by their language keys. A tag that moves changes one view,
and a scenario reads as the gestures a user makes.

What only the drawn frame shows is read from it: `screen.frame_pixels()` hands over the next frame, which is
how a menu popup's width is measured.

## The boundaries

- **File dialogs.** A native dialog stops the queue while it stands, so a scenario queues its answer before
  the gesture that opens the dialog, and the stand-in answers at once. An answer names a folder that stands
  on the disk, as a native dialog's does, and a save may pick one of the file types the dialog offers by
  its name.
- **Audio.** The default output device plays into silence in real time, so playback runs and nothing is
  heard. It is the one device the application finds on every machine: the scenario's ALSA reads a
  configuration of its own, which keeps the machine's sound cards and sound server outside the run, and a
  clock returns each write and each stop when a device would. JACK looks for a server no one runs and
  starts none, so a JACK server on the machine stays outside the run too. A scenario can start on a
  machine offering no device at all, or on one whose device refuses every stream, with the same
  configuration in place.
- **Programs.** An audit hook refuses every program the application tries to start: a file manager, a
  browser or a dialog tool would open on the desktop around the run. A shared library lookup passes, and
  so do the stand-ins below.
- **The file manager.** Stand-in programs lead the search path: `xdg-mime` names a file manager, and that
  file manager and `xdg-open` note each path they are asked to show. The application's own reveal code
  runs, and `screen.revealed()` reads what it showed.
- **The window manager.** The scenario's X server runs none, so `screen.close_window()` sends the request
  a title bar's close button sends.
- **Table highlights.** DearPyGui holds a table's row, cell and column highlights as table state and
  reports whether one stands, so the calls laying and lifting them are wrapped from the first frame on, and
  `screen.table_highlights()` reads each highlight standing with its color.

## Holding work in flight

A gesture made while work runs is only proven if the work is provably still running when the gesture
lands. A hold keeps it there: a stand-in decides **when** the work lands and never **what** it computes.
A held conversion walks the stages a real one reports and stops halfway through matching, and a held
folder scan meets the folder's entries and then one entry after another that is no recording. Each goes
on reporting while it is held, so Stop and Cancel are heard where the real work hears them. A held rebuild
of an edited channel waits on its worker before it computes, so the edit is drawn while it is on its way,
and the real rebuild runs once it is released. A scenario standing for a rebuild that breaks lets the held
rebuilds go as that failure, which reaches the application the way a rebuild that raised does. A held
export stops at one report of its stages, after its window has heard the stage, and goes on answering a
cancel there; a scenario can move the report it stops at, to land a cancel between two files. A hold lasts
until the scenario releases it, and every hold is released before the scenario leaves, because leaving
waits for the work in flight. A scenario asks for a hold through its fixture: `conversion_hold`,
`scan_hold`, `regeneration_hold` or `export_hold`.

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
- **Held press.** What does a press still down when the screen changes do to what comes under the pointer?
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

## How the scenarios are laid out

`tests/screens/` has a package per area of the application (`application`, `exports`, `history`,
`instructions`, `interface`, `main`, `prompts`, `reconstructions`, `sequencer`), and an area has a package
per subject.
A subject package holds one file per responsibility: the classes in a file prove one family of rules of
that subject, and a file that grows past about 300 lines or starts answering a second question is split
by subject. A file name says its responsibility, such as `test_note_keys.py`.

What several files of a subject share sits in modules of the package, written once two files need it:

| Module | Holds |
|---|---|
| `constants.py` | Scalar `Final` constants and language keys |
| `cases.py` | Case dataclasses, followed by the tables built from them |
| `steps.py` | Steps, readings and the builders of a world |
| `conftest.py` | Fixtures every file of the package uses, such as `world` and `startup` |

What several areas share lives in `automation/vocabulary/`, one module per area: the keys of
the dialogs and their messages, of the converter and of playback. The names of the seeded recordings
stand with the seeds, in `tests/suite/screens/seeds/`.
A value that one file alone uses stays in that file. Constants stand directly under the imports in every
module, so a reader meets the values before the code that uses them; the tables of `cases.py` follow the
types they are made of. A case in `tests/integration/tooling/` holds that order. Scenario files import from
`constants.py`, `cases.py`, `steps.py` and the vocabulary, and never from one another.

The driver under `automation/` follows the same rules: a package per concern (`application`, `boundaries`,
`holds`, `plugin`, `views`, `steps`, `worlds` for the world type and the empty world, and the DearPyGui layer
with its `gestures` and `items`), and a module per responsibility inside it. So does the scenarios' material
under `tests/suite/screens/`, with `seeds` and the `worlds` built from them.

### Docstrings

A docstring tells a reader what is tested, how the scenario goes and what is expected, in a few plain
sentences.

- A test class opens with the rule it proves, told from the user's side. A second sentence gives the
  logic where the method names leave it open: the setup, the gestures and the witness a negative ends with.
- A test method gets one sentence on what is expected where its name does not already say.
- A fixture says what the home holds or what opens at start.
- A step or a reading says what it does and what it leaves behind.
- A case type says what one row means, and each of its fields what it holds.
- The steps defined inside a test carry their gesture as their name and need no docstring.

## Running and watching

`make screens` runs every scenario across a few workers, each on an Xvfb of its own. Each worker draws
on the processor, so CI runs two of them, which leaves each application more of a small runner's processors
for its frames. `make system-deps`
installs Xvfb with the other development packages on Linux, and a missing server is named when the run
starts. The scenarios run on Linux, and [the ledger](../bugs-and-todos.md) holds the other platforms.

To follow a scenario as it plays, draw on Xephyr, which opens its screen as a window on the desktop:

```
SAMPLETONES_SCREENS_DISPLAY=xephyr uv run python -m pytest tests/screens --no-cov -k display_settings
```

A scenario's home is scratch: it is built from the scenario's world in a homes folder made for each
worker under the system's temporary folder, whose path holds no hidden folder, so the application's
browsers reach it from a worktree under `.worktrees/` too, and it goes once the scenario ends. A homes
folder inside a hidden folder is refused, and `SAMPLETONES_SCREENS_HOMES` points the run at another
parent. The application's process keeps the machine's own temporary folder, as it does on a user's
machine, since the socket files a conversion opens there need a short path. The worker's folder is
named after its process, and each worker's first scenario removes the folders whose process has gone,
such as a crashed worker's, and leaves another live run's alone. A folder a scenario left locked opens
again before its home is copied and removed.

What a run keeps lies under `build/screens/`, in a folder named after the test: the reports, and when the
scenario failed, a screenshot of the last frame and a copy of the home it left. A copy that lost files
leaves a note beside it. `screen.capture` keeps a picture as evidence of a look, for a pull request rather
than an assertion. `SAMPLETONES_SCREENS_KEPT` moves that folder, and `SAMPLETONES_SCREENS_SCREEN`, read as
`WIDTHxHEIGHT`, sizes the virtual screen, so a run made for another purpose keeps apart from the scenarios'.

## Who governs what

| Concern | Owner |
|---|---|
| A scenario per process, its reports | `automation/dearpygui/isolation.py`, `plugin/hooks.py` |
| The fixtures a scenario asks for | `automation/plugin/fixtures.py`, `plugin/hold_fixtures.py` |
| The render thread crossing and waiting | `automation/dearpygui/bridge.py` |
| What a user can reach | `automation/dearpygui/reach.py`, `semantic.py` |
| The gestures | `automation/dearpygui/hand.py` and `gestures/`: `arrival.py` (waiting and confirming), `witness.py` (what Dear ImGui counted), `pointer.py`, `scrolling.py`, `keyboard.py` |
| What a reading says of an item | `automation/dearpygui/items/`: `reading.py`, `regions.py`, `texts.py`, `colors.py`, `viewport.py` |
| The display a worker draws on | `automation/dearpygui/display.py` |
| The application under test and how it ends | `automation/application/` |
| The stand-ins at the boundaries | `automation/boundaries/` |
| Work held in flight | `automation/holds/` |
| The after-checks | `automation/checks.py` |
| What a scenario holds and reads | `automation/screen.py`, `views/`, `steps/` |
| The world type and the empty world | `automation/worlds/home.py` |
| What a scenario's home holds | `tests/suite/screens/worlds/`, and the files it seeds in `seeds/` |
| The words several areas share | `automation/vocabulary/` |
| The window manager's requests | `automation/dearpygui/windows.py` |
