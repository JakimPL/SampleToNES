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
* Release-build deployment config: `behavior/deployment.yaml` ships development
  values (`log_level: DEBUG`, `strict_history: true`) and PyInstaller bundles the
  same file; packaging needs a step that swaps in a release variant
* `ModuleExportError` domain type for the FamiTracker builder, replacing the bare
  `ValueError`s it raises for format limits, so `ProjectCoordinator._export_module`
  can catch a domain error

## Architecture

* Per-tab undo routing (analogous to `PlaybackRouter`) once standalone
  reconstruction documents gain their own history

## Bugs

* No refreshing after library generation
* Finished unclosed reconstruction prompts before exiting
