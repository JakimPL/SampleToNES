## To-dos

### Features

* Functional grid sequences
* Delete library/reconstruction (with confirmation)

### Navigation

* Interface scale
* Tree navigation using keys
* Waveform LOD for zooming
* About panel
* Gray out reconstruction when in progress

### Workflow

* Undo/redo
* Volume mixer

### Technical

* API documentation
* Code documentation (docstrings)
* Backward compatibility: library/reconstruction upgrade scheme
* Improved library file managing

## Bugs

* No error message while loading a corrupt library
* Finished unclosed reconstruction prompts before exiting

## Architecture

* **`view_model/reconstruction/data.py` — `ReconstructionData` is a domain type misplaced in `view_model/`.**
  `ReconstructionData` is a frozen dataclass wrapping `Reconstruction`, `Config`, `original_audio`, and `FeatureData` — it is a domain container, not a UI projection. It is used directly by `ReconstructionManager`, `ReconstructionCoordinator`, and `RegenerationService`. Its location in `view_model/` causes `services/regeneration.py` to import from the view-model layer, which violates the service-layer boundary rule. `ReconstructionData` (and `FeatureData`) should be moved to `logic/reconstruction/` or a shared domain types module.

