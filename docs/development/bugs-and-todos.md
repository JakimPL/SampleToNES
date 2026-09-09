## To-dos

### Navigation

* Interface scale
* Tree navigation using keys
* Moving through the converter's list of gathered recordings with the keyboard. The list holds one
  row picked out, which is a selection rather than a position: `ConverterState.selected` names it,
  a click sets it, and `Del` reaches it through the `SOURCES` key scope
  (`ui/panels/main/converter/listing.py`). What is missing is a cursor the arrow keys move, `Home`
  and `End`, and a folder opened and closed from the keyboard — the last of which the list answers
  for on its own, since which folders stand open is `OpenFolders` in `ui/elements/stems/` rather
  than anything the model records.
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
* Picking several rows of the converter's list at once, so a group leaves or settles in one gesture
  rather than a row at a time. The widget family already draws a multi-pick reading —
  `StemsListOffer.picking` with `picked_keys` and `picking_room` in `view_model/shared/stems.py` —
  built for the mix chooser and switched off for `GATHERED_SOURCES`. What a converter pick needs
  beyond it is a pick with no ceiling, since the chooser's is the room a mix has, and the gestures
  the list already offers one row reaching every picked row: removal, a channel box, and the
  settings card, which names a single row today.
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
  for projects, a current document rewritten backward into the older shape — so a step is held
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
  gap is that a case reading the coordinator's own behavior cannot see a hook left unset. Building
  the object in that file is what closes it.
* Principle 6 was rewritten once on the premise that a widget's callback arrives on the render
  thread, reasoned from `manual_callback_management` never having been enabled. A probe reads the
  opposite: a global mouse handler reports one thread identifier and the render loop another, so
  DearPyGui answers a gesture on a thread of its own and every callback that rebuilt widgets was
  racing the renderer. Manual callback management is now on and the frame runs what DearPyGui
  gathered, which makes the principle true rather than merely stated. What a gesture costs is now
  paid between frames, so a callback heavy enough to be felt is one to spread across frames itself.
* `state.last_paths.library` is written and never read. `SessionManager.set_library_path` records
  the directory a library was chosen from, and `get_library_path` is reached by no caller: the
  dialog that would open there takes its starting directory from the advanced settings panel
  instead. Either the dialog reads the remembered path or the field and its pair of accessors go.
* Which recordings a mix is built from is decided in `ui/` until **Add** is pressed. The chooser
  holds the pick as its own `_picked` set and asks `StemsListViewModel` how a gesture moves it —
  `picking_of`, `reaches` and `picking_settled` compute the transitions in `view_model/shared/`,
  which is a projection answering a question about state rather than describing one. The logic
  layer hears the answer and nothing before it, so a pick abandoned by closing the window was
  never state anyone else could read. Principles 3 and 4 put that machine in `logic/`, with the
  chooser drawing what a view model says and reporting the gesture; moving it is a phase rather
  than a patch, because the dialog is what drives the pick today.
* `ConverterMessages` reads the strings it puts to a reader once, at construction, where principle
  8 has text resolve at the point of use so a language change takes effect on the next read. The
  stage names and the status lines are cached as fields; the templates the run fills are read live.
  This predates the converter's rebuild — the class it replaced cached the same way — and the fix
  is the same either way: read each key where it is used, and let the manager answer.
* `FolderScan` (`logic/main/sources/scan.py`) runs a long directory read on a worker and reports
  back, which is what `services/` is for, while standing in `logic/`. It reports through optional
  hooks rather than the result union, and its reports arrive on the worker's own thread, so the
  coordinator crosses to the render thread on its behalf rather than the walk posting to
  `CallbackQueue`. It stays there because it is short and the tab is its only caller; what a move
  would buy is the exhaustive `match` every other long operation reports through.
* Every gesture re-derives the whole setup. `ConverterLogic._settle` reads the gathered sources
  into rows and follows the state to its destination, which builds one batch entry per recording
  still holding a channel. `tests/benchmarks/test_converter_load.py` holds both to the length of
  the list, and reads about 40 ms and 50 ms on a folder of ten thousand with the collector held
  off. What a reader pays is more: a gesture hands `_settle` a state whose recordings are new
  objects, so the readings are taken cold and the collector's own share falls inside them —
  measured together at roughly a quarter of a second per gesture at that size, before a widget is
  touched. All of it is repeated work, since what changed was one recording. Answering it means
  holding the rows against the gathering that produced them and deriving entries for the
  recordings a gesture actually moved.
* Several directories under `ui/` carry modules without an `__init__.py`, which leaves each one a
  namespace package. A tool reading the tree treats such a directory as a root it can import from,
  so a module inside one answers for a standard-library name of the same word: `ui/elements/trace.py`
  stands against `trace` this way, and `ui/elements/graphs/layers/array.py` did against `array`
  until it was given a package of its own. Giving each directory an `__init__.py` closes the
  whole class.

## Bugs

* A reconstruction written by an earlier 0.3.2 build cannot be opened, and the pending upgrade step
  is not where that is answered. The record stamped data version 2.2 while a stem entry still stated
  its channels on the entry itself; the entry now carries a `StemSettings`, and a step from 2.1
  never runs on a file already stamped 2.2. Data version 2.2 therefore means the current shape, and
  a file stamped 2.2 in the earlier one is a mid-development artifact rather than a release the
  format owes compatibility to — the files that existed were removed. What a release shipped is
  unaffected: a v0.3.1 file carries data version 2.1 and no stems record, so the step synthesizes
  one in the current shape. The lesson holds for the rest of 0.3.2: a shape that moves between
  releases moves inside the pending step, and a build writing the pending version writes the shape
  that step produces.

* The converter's card jumps for about two frames the first time a folder is opened in a list that
  held one from the outset. `GUIStemsList._rebuild` returns early on exactly `_windows()` —
  `collapse_levels and not holds_folders` — which is the same condition under which `_plain_rows`
  answers with the row count, so `draw_whole` is always handed none and the shared `RowGeometry`
  goes unmeasured until a folder's own region measures it. That first slice is taken at the
  `MINIMUM_ROW_PITCH` floor, which reaches far more rows than the region shows, and the settle after
  it re-slices at the reading. Either the whole-drawn path reports the rows of its plain segments,
  or the geometry opens from `layout.name_height` rather than the floor.

* Every right-click leaves a popup window behind. `ui/elements/context_menu.py` opens an untagged
  `dpg.window(popup=True)` that nothing deletes, so the item tree grows by a menu's worth of widgets
  and their captured closures per gesture, for the life of the run. It is shared by the converter's
  list, the file browsers and the samples panel. The popup needs a tag of its own per panel and a
  deletion before it is built again.

* No refreshing after library generation
* Misaligned dialog boxes sizes at initialization
* Audible noise instructions when matching near-silent samples for FFT γ0
