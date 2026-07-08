## To-dos

### Features

* Delete library/reconstruction (with confirmation)

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming
* Gray out reconstruction when in progress

### Tracker

* Selection: copy, cut, delete and paste

### Workflow

* Volume mixer

### Technical

* API documentation
* Code documentation (docstrings)
* Backward compatibility: library/reconstruction upgrade scheme
* Respecting FamiTracker limitations
* Per-tab undo routing (analogous to `PlaybackRouter`) once standalone
  reconstruction documents gain their own history

## Bugs

* No refreshing after library generation
* Finished unclosed reconstruction prompts before exiting

## Architecture

Behavioural-contract deviations from `architecture.md`, tracked until paid off. The
tab-layout ownership refactor resolves the layout entries phase by phase; remove each entry
as its phase lands.

* **Tab layout authored outside `create_tab()`.** Host panels build multi-card sub-layouts
  and host other panels — `GUIMainPanel` (config + reconstructor + advanced + converter),
  `GUIInstructionPanel` (player + waveform + spectrum), `GUIReconstructionPanel`
  (player + audio + plot), `GUIInstructionDetailsPanel` (two cards) — and the sequencer
  coordinator fills the grid panel's empty child window through
  `parent=TAG_SEQUENCER_GRID_PANEL`. Tab layout belongs solely to `create_tab()`.
* **SURFACE bound by several owners.** `TabColumns` owns the columns' depth binding — the
  recessed GROUND theme, and, until each side column's content moves into a card, the raised
  SURFACE theme on the left (and reconstructions' right) columns. SURFACE is still bound
  directly by the instruction and reconstruction host panels, by single-card panels
  themselves, and by the sequencer coordinator's card loop. The `card()` context manager
  becomes SURFACE's single owner.
