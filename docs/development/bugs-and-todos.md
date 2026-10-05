# Bugs and to-dos

This is the working ledger of what is still owed: to-dos, deviations from the architecture, and known
bugs. Read it before starting work in an area. Add an entry when a change knowingly leaves something
behind. Each entry says what is owed and why, and the code and the change that closes it hold the rest.

## To-dos

### Navigation

* Interface scale
* Keyboard navigation of the trees, and of the converter's list of gathered recordings: a cursor the arrow
  keys move, `Home` and `End`, and folders opened and closed from the keyboard.
* Waveform LOD for zooming
* Drag and drop of browser nodes onto views, such as a reconstruction onto Samples.
* Tabs for several reconstructions in the Reconstruction view.
* Application installation progress bar

### Tracker

The first two entries are the settings an imported `.fti` reports as left behind (see
[FamiTracker export](../formats/famitracker.md#c-reading-an-instrument-file)). Each one closed is a
dimension the import starts carrying.

* Release points. A note-off cuts the channel today, so a release segment has nowhere to play.
* Arpeggio modes. Fixed, relative and scheme arpeggios import as absolute offsets today.
* Compatibility options for the FamiTracker export, so a module plays as the app does where FamiTracker's
  own rules differ, such as how it rounds a pulse level and where it places the longer rows of an uneven
  tempo.

### Workflow

* Waveform construction preview: a waveform drawn from the partial reconstruction while the converter
  reconstructs a single file.
* Picking several rows of the converter's list at once, so a group leaves or settles in one gesture.
* Selecting parts of a reconstruction's waveform to crop, trim, cut and paste them along with their
  instructions.
* Marking broken files where the browsers list them: a reconstruction that fails to load, one whose
  recordings are missing and a recording that cannot be read could stand in a warning or an error color,
  so the reader learns before trying to open or play one.

### Features

* In-application guide/tutorial
* Language selector
* Reading only the bins the refinement asks for. The pitch refinement bends notes by reading the audio's
  spectrum, and it transforms every frequency bin the spectrum covers while using a handful per frame,
  which is a tenth or more of a short conversion on a CPU build.
* Keeping the recordings a stopped folder scan has found, so stopping a long walk keeps the count the reader
  watched climb.
* Calibrating the pitch refinement. The settings that decide how a pitch reading bends a note (a
  confidence threshold, a change weight and a window) are chosen by hand, and
  [the calibration](../tools/calibration.md) could measure them. The change weight trades vibrato against
  jitter.

### Technical

* Screen scenarios on Windows and macOS. They run on Linux alone, and whether DearPyGui opens its window on
  GitHub's Windows and macOS runners is unverified.
* An upgrade path for the configuration and the session state. A file an older build left behind is read
  as the loader happens to, and no archived files of older builds test it.
* The element enums that outlived their keys. The language-keys check treats a key named through an
  element enum as the whole enum, so a key no call uses goes unnoticed. Spelling each key at its call site
  makes the check exact.
* Per-tab undo routing
* A history of its own for a standalone reconstruction document, one loaded from disk and not opened as a
  project sample. An edit to such a document is undoable nowhere ([undo](application/undo.md)), so an edit
  that silences a channel or lets a recording go is reversible only by reloading the file.
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
* The tab coordinators' and the application's unit tests build their object through `__new__` and fill its
  private fields by hand, so a case describes a method and not the wired object, and a hook left unset goes
  unseen.
* Which recordings a mix is built from is decided in `ui/` until **Add** is pressed. The chooser holds the
  pick as its own set and asks the view model how a gesture moves it, so a projection computes state
  transitions. The logic layer hears only the answer. Principles 3 and 4 put that machine in `logic/`,
  with the chooser drawing what a view model says and reporting the gesture. Moving it is a phase and not
  a patch, because the dialog drives the pick today.
* Every gesture in the converter re-derives the whole setup, so a gesture costs fifteen times as much on
  10,000 recordings as on 1,000, much of it in garbage collection. A gesture hands
  `ConverterLogic._rewrite` a state whose recordings are new objects, and the rows and the batch entries
  are read from it cold. Holding the rows against the gathering that produced them, and deriving entries
  for the recordings a gesture moved, closes it.

## Bugs

* The Sample column shows no sample on a frame's first rows, since its reading starts over at each frame. It
  offers no transpose or volume there, while playback applies them to the sample the previous frame left
  sounding.
