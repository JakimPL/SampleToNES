## To-dos

### Features

* Delete library/reconstruction (with confirmation)

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming

### Tracker

* Selection: copy, cut, delete and paste

### Workflow

* Volume mixer

### Technical

* API documentation
* Code documentation (docstrings)
* Backward compatibility: library/reconstruction upgrade scheme
* Respecting FamiTracker limitations
* Per-tab undo routing

## Bugs

* No refreshing after library generation

## Architecture

Known deviations from the design contracts, recorded here until they are paid off (per
`architecture.md`). The ledger, not the codebase, is the memory of what is currently out
of line.

* **Configuration package** — the `sampletones_config` tree does not yet satisfy the
  rules in `config-organization.md`. The tracked list is that document's
  § Known deviations checklist (feature-area directories, the missing `reconstruction`
  section, per-tab geometry ownership, the split responsive baseline, `choice` naming,
  the `behavior` domain fold-in, and the dead `VERSION_CONFIG_PATH`).
