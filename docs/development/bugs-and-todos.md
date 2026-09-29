# Bugs and to-dos

This is the working ledger of what is still owed: to-dos, deviations from the architecture, and known
bugs. Read it before starting work in an area. Add an entry when a change knowingly leaves something
behind. Each entry says what is owed and why, and the code and the change that closes it hold the rest.

## To-dos

### Navigation

* Interface scale
* Tree navigation using keys
* Keyboard navigation of the converter's list of gathered recordings: a cursor the arrow keys move, `Home`
  and `End`, and folders opened and closed from the keyboard.
* Waveform LOD for zooming
* Drag and drop
* Multiple Reconstruction views
* In-project sample selection in Reconstruction view
* Application installation progress bar

### Tracker

The first two entries are the settings an imported `.fti` reports as left behind (see
[FamiTracker export](../formats/famitracker.md#c-reading-an-instrument-file)). Each one closed is a
dimension the import starts carrying.

* Release points. A note-off cuts the channel today. A release segment needs the playback walk, the NSF
  driver and `NoteOff` to gain one.
* Arpeggio modes. A sequence's `setting` byte says absolute. Fixed, relative and scheme need an enum of
  their own, and scheme needs the item bit-packing FamiTracker gives it.
* The sample column reads the sample still playing from the top of each frame, so a frame's first rows
  take no transpose or volume while playback still carries the previous frame's sample.

### Workflow

* Waveform construction preview for single-file conversion
* Picking several rows of the converter's list at once, so a group leaves or settles in one gesture. The
  widget family already draws a multi-pick reading, built for the mix chooser. A converter pick needs one
  with no ceiling, and every gesture the list offers one row must reach each picked row.
* Selection operations on a reconstruction
* Reconstruction trimming

### Features

* In-application guide/tutorial
* Language selector
* Reading only the bins the refinement asks for. The pitch reading transforms every bin the spectrum
  covers and uses a handful of them per frame. On a CPU build one transform is a tenth or more of a short
  conversion. Restricting the kernel to the rows the chosen notes name is a slice. The care is that the
  union of harmonic bins over a whole stream is wider than any one frame's.
* Keeping what a stopped folder scan found. Stopping a long walk drops the recordings met so far, while the
  gathering already answers with them. Handing that list on would let a reader stop a long walk and keep
  the count they watched climb. It needs the empty branch of the read reworked beside it, since a stop
  before the first recording is a different answer from a folder with none.
* Calibrating the pitch refinement. The refinement's confidence threshold, change weight and window are
  chosen by hand, and [the calibration](../tools/calibration.md) could measure them beside the criterion
  blend. The change weight is the one with an audible trade-off: it decides how large a one-frame
  excursion the walk follows and how large it absorbs, which is vibrato against jitter.

### Technical

* Leading the calibration report with `mr-loudness-dB`. The report lists `mr-auditory-dB` first, which
  reads silence as closer to a tone than any render. The order changes once by-ear ratings of a sweep hold
  the loudness-weighted referee at ρ ≥ 0.6 in every category. A listening round scored `polyphony-chord`
  6–7 dB better on a render that dropped the noise channel entirely, so the bar is unmet.
* An axiom that a recording built with noise reconstructs with the noise channel sounding. The corpus
  knows which items were synthesized from noise, and the render records hold the per-channel timelines.
  Such a test would fence the criterion against noise deafness without a listening round, as
  `referee/test_axioms.py` does for the referees.
* API documentation
* Code documentation
* What a build makes of the configuration and the session state an older one left behind. Neither has a
  version, so neither travels an upgrade chain or has an archived corpus. A `state.yaml` naming a panel
  that has since gone, or a configuration missing a setting added since, is read by whatever each loader
  happens to do with it.
* The element enums that outlived their keys. An element enum is named only where a `_label(element)`
  helper takes one, and the language-keys check expands such a helper over the whole enum, so a member no
  call names is reached all the same. Spelling those keys literally at the call site makes each entry
  exactly checkable and retires the enums that remain.
* Respecting FamiTracker limits at the writers. A target format's ceilings belong to the code that writes
  it, and today only the sequence-length ceiling follows that rule. The instrument, sequence and pattern
  counts should follow it too, so a project past one of them is reported to the reader and not refused by
  the writer.
* Per-tab undo routing
* A history of its own for a standalone reconstruction document, one loaded from disk and not opened as a
  project sample. The engine is session-scoped to a project, so an edit to such a document is undoable
  nowhere. Giving it a stack reuses the same engine ([undo](application/undo.md)).
* In-application console
* Improve performance of the browser's favorite scan of the entire tree per click

## Architecture

Where the codebase stands apart from [`architecture.md`](architecture.md). A deviation is recorded here
once review has seen it and let it stand, so this section, and not the code, is the memory of what is
currently out of line. An entry leaves when the code meets the contract again.

* The two sequencer grids implement the same machinery twice. The order and tracker panels each declare the
  same block and channel hooks, build the same `ChannelSwitch`, tint a channel the same way, and run the
  same held-pointer drag, right-click hit-test and key dispatch. The shared `ui/panels/sequencer/grid/`
  package is where these belong, and `# TODO: to abstract` markers stand at the blocks. Pylint's
  duplicate-code report names each pair.
* `application.py` and `ui/elements/tree/tree.py` each hold several concerns in one module, past the size
  at which the sequencer panels were divided into subpackages. Each divides the same way: a module per
  concern, with the class that stays holding the collaborators and the public surface.
* The Main tab's public surface renames several calls on its way to a panel (`refresh_converter_view`,
  `is_converter_panel_visible`, `refresh_browser`). Those are the tab's own face, and the inbound callbacks
  the Coordinators contract governs are forwarded as they stand. The open question is whether the face
  needs those names at all, or whether the application should ask for the thing and not for the refresh of
  it.
* `dpg_get_item_parent` catches `Exception`, where the Error Handling Policy leaves the broad catch to a
  service's top-level task wrapper. Its docstring says why, and the catch narrows the day DearPyGui raises
  a type of its own.
* Every fixture in the Main tab coordinator's tests builds the coordinator through `__new__` and fills its
  privates by hand, so those cases describe a method and not the wired object. A case reading the
  coordinator's own behavior cannot see a hook left unset. Building the object in that file closes the
  gap.
* Which recordings a mix is built from is decided in `ui/` until **Add** is pressed. The chooser holds the
  pick as its own set and asks the view model how a gesture moves it, so a projection computes state
  transitions. The logic layer hears only the answer. Principles 3 and 4 put that machine in `logic/`,
  with the chooser drawing what a view model says and reporting the gesture. Moving it is a phase and not
  a patch, because the dialog drives the pick today.
* `ConverterMessages` reads the strings it shows a reader once, at construction, where principle 8 has text
  resolve at the point of use. The stage names and status lines are cached as fields, and the run's
  templates are read live. The fix is to read each key where it is used and let the manager answer.
* `FolderScan` runs a long directory read on a worker and reports back, which is work that `services/` exists for,
  while it stands in `logic/`. It reports through optional hooks and not the result union, and the
  coordinator crosses to the render thread on its behalf. Moving it would buy the exhaustive `match` every
  other long operation reports through.
* Every gesture in the converter re-derives the whole setup. A gesture hands `ConverterLogic._rewrite` a
  state whose recordings are new objects, so the rows and the batch entries are read from it cold, and the
  garbage collector's own share falls inside them. On a very large folder that is long enough to feel as a
  pause before a widget is touched, and all of it repeats work, since one recording changed. The answer is
  to hold the rows against the gathering that produced them and derive entries for the recordings a gesture
  moved.

## Bugs
