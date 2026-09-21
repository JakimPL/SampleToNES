## To-dos

### Navigation

* Interface scale
* Tree navigation using keys
* Moving through the converter's list of gathered recordings with the keyboard. The list holds a
  selection rather than a position (`ConverterState.selected`), so what is missing is a cursor the
  arrow keys move, `Home` and `End`, and a folder opened and closed from the keyboard.
* Waveform LOD for zooming
* Alt for scrolling graphs
* Drag and drop
* Multiple Reconstruction views
* In-project sample selection in Reconstruction view
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
  rather than a row at a time. The widget family already draws a multi-pick reading
  (`StemsListOffer.picking`), built for the mix chooser and switched off for `GATHERED_SOURCES`. What
  a converter pick needs beyond it is a pick with no ceiling, since the chooser's ceiling is the room
  a mix has, and every gesture the list offers one row — removal, a channel box, the settings card —
  reaching each picked row.
* Selection operations on a reconstruction
* Reconstruction trimming

### Features

* In-application guide/tutorial
* Language selector
* Reading only the bins the refinement asks for. `InstantaneousPitch` transforms every bin the
  spectrum covers and then reads five of them per frame, so it computes around twenty times the
  work its reading uses. On a CUDA build that vanishes; on a CPU build one transform measures a
  tenth or more of a short conversion. The kernel is a matrix of one row per bin, so restricting it
  to the rows the chosen notes name is a slice — what needs care is that the union of harmonic bins
  over a whole stream is wider than any one frame's.
* Keeping what a stopped folder scan found. `_walk` in `logic/main/sources/scan.py` reports
  `on_stopped` and returns where the reader presses **Stop**, so the recordings met so far go
  nowhere, while `_gather` already answers with them. Handing that list to `answer` instead would
  let a reader stop a long walk and keep the count they watched climb. It needs `_gather_read`'s
  empty branch (`coordinators/tabs/main.py`) reworked beside it, since a stop before the first
  recording turns up is a different answer from a folder that holds none.
* Calibrating the pitch refinement. `generation.refinement`'s confidence threshold, change weight
  and window are chosen by hand, and [the calibration](../tools/calibration.md) could measure them
  beside the criterion blend. The change weight is the one with an audible trade-off: it decides how
  large a one-frame excursion the walk follows rather than absorbs, which is vibrato against jitter.

### Technical

* Leading the calibration report with `mr-loudness-dB`. `build_referees` puts `mr-auditory-dB`
  first, which reads silence as closer to a tone than any render. The order changes once by-ear
  ratings of a sweep hold the loudness-weighted referee at ρ ≥ 0.6 in every category, which is the
  bar [the calibration](../tools/calibration.md) sets; a listening round has scored
  `polyphony-chord` 6–7 dB better on a render that dropped the noise channel entirely, so the bar
  stands unmet.
* An axiom stating that a recording built with noise reconstructs with the noise channel sounding.
  The corpus knows which items were synthesized from noise and the render records already hold the
  per-channel timelines, so such a test would fence the criterion against noise deafness the way
  `referee/test_axioms.py` fences the referees, without a listening round.
* API documentation
* Code documentation
* What a build makes of the configuration and the session state an older one left behind. Both
  carry no version at all, so neither travels a chain and neither is archived beside the stored
  formats, whose corpus is now `tests/data/compatibility`. A `state.yaml` naming a panel that has
  since gone, or a configuration missing a setting added since, is read by whatever each loader
  happens to do with it, which nothing states.
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
* A history of its own for a standalone reconstruction document — a reconstruction loaded from disk
  rather than opened as a project sample. The engine is session-scoped to a project, so an edit to
  such a document is undoable nowhere; giving it a stack reuses the same engine
  ([undo](application/undo.md)).
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
  still holding a channel. A gesture hands `_settle` a state whose recordings are new objects, so
  the readings are taken cold and the garbage collector's own share falls inside them — together long
  enough to be felt as a pause on a folder of ten thousand recordings, before a widget is touched,
  where `tests/benchmarks/test_converter_load.py` holds the warm readings to the length of the list. All of it is repeated work, since what changed was one recording. Answering it means
  holding the rows against the gathering that produced them and deriving entries for the recordings
  a gesture actually moved.
* Several directories under `ui/` carry modules without an `__init__.py`, which leaves each one a
  namespace package. A tool reading the tree treats such a directory as a root it can import from,
  so a module inside one answers for a standard-library name of the same word: `ui/elements/trace.py`
  stands against `trace` this way, and `ui/elements/graphs/layers/array.py` did against `array`
  until it was given a package of its own. Giving each directory an `__init__.py` closes the
  whole class.

## Bugs

* A channel whose every frame rests reads as standing by for the reader while `playing_channels`
  and the export still count it, so the panel and the size figures disagree about a channel whose
  volume was written down to nothing.
* `_on_bar_point_clicked` composes a raw-data tag the text field does not carry, so its write
  finds nothing and the field catches up only when the edit returns through the regeneration.
* A reconstruction written before the recorded sources moved onto the stems record reads with
  none of them, so the browser, original playback and the Stems card see a detached document
  where the file names its recordings under the top-level `audio_filepath`. Folding those paths
  onto `StemsData.sources` is what the reconstruction 2.2 conversion step still owes, along with
  the per-entry drives and channel count a mid-branch 2.2 file carries at the top of its setup.
* `ReconstructionStage.RENDERING` keeps the weight it was measured at while a conversion no longer
  renders, so a bar covers that share faster than the eight parts in a hundred `STAGE_WEIGHTS`
  gives it. Re-measuring the four stages over whole runs is what settles the new figures.
* `_heard_stream` reads a resting frame as heard whoever is unchecked, so a channel whose last
  frame is a rest keeps its reading open to the end: the frames an unchecked recording held come
  back as silence instead of being cut, and the instruments panel, the size figures and an export
  all measure that longer sequence. The rule is there so a channel written down to rests alone
  stays in play, which the cut has to keep.
* `StemColors.for_stem` paints a resting stretch in `stem_rest`, the color matching the ribbon's
  ground so a rest reads as a gap under the waveform. The band beneath the instruments bars reuses
  it over `plot_background`, which differs in every palette — `#aab0bb` against `#ffffff` in the
  light one — so a rest shows there as a solid bar where it should be a gap.
* The error dialog states a height of 120 and its traceback box adds 400, so **Show traceback**
  grows it past the 800-tall client the application opens at its smallest and its buttons fall
  below the screen. `center_when_settled` has ended by then, so the dialog grows downward from
  where it stood rather than re-centering on the new height.
