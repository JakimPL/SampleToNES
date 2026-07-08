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

* **Structural depth bound outside `card()` in two remaining places.** The `card()` context
  manager (`ui/elements/layout/card.py`) binds the raised SURFACE theme for every bordered
  content card, replacing the host-panel self-binds and the sequencer coordinator's card loop.
  Two owners still bind a structural surface directly: `TabColumns` binds SURFACE to the side
  columns (the left library/browser/explorer columns and reconstructions' right instruments
  column), whose `border=False` tree content draws its frame from the column rather than a
  card; and the player toolbar cards bind their toolbar surface through `centered_card`.
  Phase 5 moves the side content into cards (flipping those columns to GROUND) and Phase 6
  folds the remaining `centered_card` callers onto `card()`.
