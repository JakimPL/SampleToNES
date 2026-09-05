## To-dos

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming
* Alt for scrolling graphs
* Drag and drop
* Multiple Reconstruction views
* In-project sample selection in Reconstruction view
* Playing a fragment by clicking on a waveform
* Application installation progress bar

### Tracker

The first two entries are also what an imported `.fti` reports as left to the file
(section C of `formats/famitracker.md`), so each one closed is a dimension the import
starts carrying.

* Release points: `NoteValue.RELEASE` stands in the FamiTracker specification while a note-off cuts
  the channel. A release segment would need the playback walk, the NSF driver and `NoteOff` to gain
  one.
* Arpeggio modes: a sequence's `setting` byte states absolute. Fixed, relative and scheme need an
  enum of their own, and scheme needs the item bit-packing FamiTracker gives it.
* The bend reaching the NSF planes. Each tone channel carries a bend plane and the driver adds
  what it holds to the divider, but the encoders still leave the dimension to the note:
  `registers/playable.py::playable` states that once, and every encoder below reads frames
  carrying no bend. Filling the plane means the register encoders holding the bent divider and
  `PitchTable` naming a divider as the nearest pitch beside a signed residual. Until it lands, an
  NSF renders a bent note at the note's own divider.
* The bend in a Bitphase export. `formats/bitphase/envelopes.py` states the three dimensions it
  writes; `NesInstrumentRow` already carries `tone_add` and `tone_accumulation`, so the mapping is
  confined to that module.
* A transpose or a volume typed in the sample column of a row holding no sample reaches every
  channel. The column summarizes the channels its samples cover, and a row covering none falls
  back to all four so a value typed there lands somewhere; the reference slot keeps the narrower
  reading and stays empty.

### Workflow

* Waveform construction preview for single-file conversion
* Selection operations on a reconstruction
* Reconstruction trimming

### Features

* In-application guide/tutorial
* Language selector
* Verifying a bend against the criterion. The plan for the refinement carried a guard: render the
  bent candidate, score it, and keep the bend only where the cost improves. It was measured and
  left out. The criterion agreed with the reading on **every** bent frame of both a matched and a
  mismatched target, so the guard rejects nothing; and one extra render-and-score per bent frame
  measures around **2.1 s per second of audio**, against a whole conversion's ~1.2 s, so it would
  nearly triple a run to change no decision. It is worth revisiting only against material where the
  reading is shown to misfire.
* Reading only the bins the refinement asks for. `InstantaneousPitch` transforms every bin the
  spectrum covers and then reads five of them per frame, so it computes around twenty times the
  work its reading uses. On a CUDA build that vanishes; on a CPU build one transform measures a
  tenth or more of a short conversion, and a CI runner has measured it at a third. The kernel is a
  matrix of one row per bin, so restricting it to the rows the chosen notes name is a slice — what
  needs care is that the union of harmonic bins over a whole stream is wider than any one frame's.
* Calibrating the pitch refinement. `generation.refinement`'s confidence threshold, change weight
  and window are chosen by hand; `docs/concepts/calibration.md`'s experiment measures the criterion
  blend and could measure these beside it. The change weight is the one with an audible trade-off:
  it decides how large a one-frame excursion the walk follows rather than absorbs, which is
  vibrato against jitter.

### Technical

* API documentation
* Code documentation
* A backward-compatibility corpus of files older builds actually wrote. Every upgrade step is
  exercised against a payload the test builds itself — hand-written mappings for the step, and,
  for projects, a current document rewritten backwards into the older shape — so a step is held
  only to the fields it names. One archived `.stn`, `.ins` and `.stp` per shipped version, each
  written by that version and exercising every feature it could store, would hold the whole
  document to the chain and would catch a field that changed shape while no step named it.
  Configuration and session state carry no version at all, so the same corpus would state what a
  build is expected to make of a `state.yaml` an older one left behind. Reaches
  `tests/unit/sampletones_core/compatibility/` and each format's load tests.
* The element enums that outlived their keys. A lookup states its key literally, so an element
  enum is named only where a `_label(element)` helper takes one — `ui/menu.py`,
  `coordinators/project.py`, `coordinators/keybindings.py`, `ui/panels/dialogs/project_properties.py`
  and the panels beside them. The language-keys check expands such a helper over the whole enum, so
  a member no call names is reached all the same and stands unnoticed. Spelling those keys literally
  at the call site would make each entry exactly checkable and retire the enums that remain.
* Respecting FamiTracker limitations at the writers. A target format's ceilings belong to the
  code that writes that format: an envelope carries whatever length a reader wrote, and meets a
  limit where a file is built. `formats/famitracker/sequences/features.py` is where the 252-item
  sequence ceiling applies today, and it is the one place that decides what a file holds, which
  both the export's report and the instruments panel's warning read. What is still owed is the
  same treatment for the ceilings a module carries — the instrument, sequence and pattern counts
  in `specification/` — so a project past one of them is reported to the reader rather than
  refused by the writer.
* Per-tab undo routing
* In-application console
* Improve performance of browser favorite scan of the entire tree per click

## Architecture

Where the codebase stands apart from `docs/development/architecture.md`. A deviation is recorded
here once review has seen it and let it stand, so this section — rather than the code — is the
memory of what is currently out of line, and an entry leaves when the code meets the contract
again.

* The two sequencer grids state the same machinery twice. `ui/panels/sequencer/order/` and
  `ui/panels/sequencer/tracker/` each divide into a panel and its collaborators, and the panel
  modules still declare the same block and channel hooks, build the same `ChannelSwitch`, tint a
  channel the same way, and run the same held-pointer drag, right-click hit-test and key dispatch.
  `ui/panels/sequencer/grid/` is where both already reach for what they share, and it is where
  these belong; the `# TODO: to abstract` markers stand at the blocks themselves. Pylint's
  duplicate-code report names each pair, so the work is enumerable rather than a matter of
  reading.
* `application.py` and `ui/elements/tree/tree.py` each hold several concerns in one module, past
  the size at which the sequencer panels and the sequencer tab coordinator were divided into
  subpackages. Each divides the same way: a module per concern, with the class that stays holding
  the collaborators and the public surface.
* The Main tab's public surface renames several calls on its way to a panel —
  `refresh_converter_view`, `is_converter_panel_visible`, `refresh_browser`. These are the tab's
  own face rather than the inbound callbacks the Coordinators contract governs, which now travel as
  one `MainTabHooks` value and are forwarded as they stand. What is worth settling is whether the
  face wants those names at all, or whether the application should ask for the thing rather than
  for the refresh of it.
* `utils/gui/dpg.py::dpg_get_item_parent` catches `Exception` where the Error Handling Policy leaves
  the broad catch to a service's top-level task wrapper. It stays: DearPyGui raises `Exception`
  itself for an absent item rather than a type of its own, so the catch is as narrow as what it
  answers. A test pins that contract, and the day the library raises something of its own is the
  day the catch narrows.
* Every fixture in `tests/unit/sampletones_application/coordinators/tabs/test_main.py` builds
  `MainTabCoordinator` through `__new__` and populates its privates by hand, so what those cases
  describe is a method rather than the wired object. The wiring itself is exercised —
  `test_startup.py` builds the real application and drives gestures through it end to end — so the
  gap is that a case reading the coordinator's own behaviour cannot see a hook left unset. Building
  the object in that file is what closes it.
* `state.last_paths.library` is written and never read. `SessionManager.set_library_path` records
  the directory a library was chosen from, and `get_library_path` is reached by no caller: the
  dialog that would open there takes its starting directory from the advanced settings panel
  instead. Either the dialog reads the remembered path or the field and its pair of accessors go.
* Several directories under `ui/` carry modules without an `__init__.py`, which leaves each one a
  namespace package. A tool reading the tree treats such a directory as a root it can import from,
  so a module inside one answers for a standard-library name of the same word: `ui/elements/trace.py`
  stands against `trace` this way, and `ui/elements/graphs/layers/array.py` did against `array`
  until it was given a package of its own. Giving each directory an `__init__.py` closes the
  whole class.

## Bugs

* No refreshing after library generation
* Misaligned dialog boxes sizes at initialization
* Audible noise instructions when matching near-silent samples for FFT γ0
