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

* **Panels encode their own placement.** Thirteen panels compose their column parent as
  `f"{TAG_GLOBAL_TAB_*}{SUF_PANEL_*}"` in their constructors, so a panel knows which tab
  column it lives in. The coordinator should inject the parent via `create_panel(parent)`.
* **Tab layout authored outside `create_tab()`.** Host panels build multi-card sub-layouts
  and host other panels — `GUIMainPanel` (config + reconstructor + advanced + converter),
  `GUIInstructionPanel` (player + waveform + spectrum), `GUIReconstructionPanel`
  (player + audio + plot), `GUIInstructionDetailsPanel` (two cards) — and the sequencer
  coordinator fills the grid panel's empty child window through
  `parent=TAG_SEQUENCER_GRID_PANEL`. Tab layout belongs solely to `create_tab()`.
* **Duplicated column scaffold.** All four `create_tab()` bodies inline a near-identical
  ground-wrapper + gap-column table + column child-window scaffold. It belongs in one shared
  `ui/elements/layout` primitive.
* **Structural depth themes bound by several owners.** SURFACE is bound by host panels, by
  panels themselves, and by the sequencer coordinator reaching into panel-owned card tags.
  Each depth theme needs one owner: `TabColumns` for GROUND, `card()` for SURFACE.
* **Initial view population runs inside `create_tab()`.** `refresh_libraries` and the
  sequencer `refresh_view` execute mid-build; they belong in post-build initialisation.
