## To-dos

### Features

* Delete library/reconstruction (with confirmation)

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming
* About panel
* Gray out reconstruction when in progress

### Tracker

* Selecting pattern's cells
* Replacing cursor's underscore symbol
* Selection: copy, cut, delete and paste

### Workflow

* Volume mixer

### Technical

* API documentation
* Code documentation (docstrings)
* Backward compatibility: library/reconstruction upgrade scheme
* Improved library file managing
* Release-build deployment config: `behavior/deployment.yaml` ships development
  values (`log_level: DEBUG`, `strict_history: true`) and PyInstaller bundles the
  same file; packaging needs a step that swaps in a release variant
* `ModuleExportError` domain type for the FamiTracker builder, replacing the bare
  `ValueError`s it raises for format limits, so `ProjectCoordinator._export_module`
  can catch a domain error

## Architecture

* The UI layer imports `logic/` and `config/` in ~17 files (panels holding
  `PlayerLogic`, `ExplorerLogic`, `BrowserLogic`, `SessionManager`, …), against the
  layer contract; `scripts/check_import_boundary.py` therefore has no `ui/**` rule.
  Adding one requires inverting those dependencies panel by panel (the properties
  window shows the pattern: a frozen view model in, edits out through `on_commit`)
* `ui/panels/player.py` catches `PlaybackError` and renders dialogs itself; panels
  must not catch or present errors — the error path belongs in a coordinator-wired
  `on_error` hook
* History detail segments freeze language-manager text at commit time (e.g. the
  loop on/off words), so a future language switch would show mixed-language rows;
  labels already resolve at render time
* Per-tab undo routing (analogous to `PlaybackRouter`) once standalone
  reconstruction documents gain their own history

## Bugs

* No error message while loading a corrupt library
* No refreshing after library generation
* Finished unclosed reconstruction prompts before exiting
