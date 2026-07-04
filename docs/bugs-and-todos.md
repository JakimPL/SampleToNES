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

* A few panels still render dialogs themselves through `DialogsRenderer` (an
  import-legal `utils/gui` helper) where the error policy places presentation in
  coordinators — e.g. the explorer's converter-running notice; each wants the
  library-panel treatment (an intent hook, the dialog in the coordinator)
* History detail segments freeze language-manager text at commit time (e.g. the
  loop on/off words), so a future language switch would show mixed-language rows;
  labels already resolve at render time
* Per-tab undo routing (analogous to `PlaybackRouter`) once standalone
  reconstruction documents gain their own history

## Bugs

* No refreshing after library generation
* Finished unclosed reconstruction prompts before exiting
