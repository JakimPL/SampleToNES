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

* Pitch and hi-pitch envelopes: a per-tick period bend, where an instruction's pitch is a whole
  semitone. Sounding them needs a sub-semitone offset in the instruction model and raw timer values
  in the NSF planes, which reaches the reconstruction search space, the instruction library and the
  compression pitch table. The two sequences reach a tracker file today and are written empty.
* Release points: `NoteValue.RELEASE` stands in the FamiTracker specification while a note-off cuts
  the channel. A release segment would need the playback walk, the NSF driver and `NoteOff` to gain
  one.
* Arpeggio modes: a sequence's `setting` byte states absolute. Fixed, relative and scheme need an
  enum of their own, and scheme needs the item bit-packing FamiTracker gives it.
* A loop point per envelope: a voice states one point, applied to every populated sequence.
* A sample's loop point is offered as a switch in the voice list, though the model carries the
  point for both kinds of voice.
* Exporting a hand-written instrument as an instrument file from the Reconstructions tab.
* `SubColumn.INSTRUMENT` names the first slot of both tracker column kinds, and the two hold
  different things: the voice id under the Voice column, and the note on a channel column. One
  name for both is wrong half the time, and splitting it reaches the layout keys
  (`sequencer/colors.yaml`, `sequencer/tracker.yaml`) and their DTOs, so it is a question of its
  own rather than part of naming a voice.

### Workflow

* Waveform construction preview for single-file conversion
* Selection operations on a reconstruction
* Reconstruction trimming

### Features

* In-application guide/tutorial
* Language selector

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
* Tree node attributes stand outside the type checker. `TreeNode` derives from `anytree.Node`,
  which ships no types, so mypy reads every attribute of a node — and of `FileSystemNode`,
  `ConfigNode`, `LibraryNode`, `GeneratorNode` — as `Any`, and a misspelled one passes the gate.
  A rename sweep spelling `GeneratorNode.generator_name` as `channel_name` reached the running
  application that way. Declaring the attributes on a typed base, or stubbing the part of
  `anytree` the tree uses, would put node reads back under the checker. Reaches
  `sampletones_core/structures/tree/`.
* Respecting FamiTracker limitations
* Per-tab undo routing
* In-application console
* Improve performance of browser favorite scan of the entire tree per click

## Bugs

* No refreshing after library generation
* Misaligned dialog boxes sizes at initialization
* Audible noise instructions when matching near-silent samples for FFT γ0
