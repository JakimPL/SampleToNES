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

* **`shell.py:353` — `get_current_player()` always returns `None`.**
  `_TAG_TABS.get(self.get_current_tab())` looks up a `Tab` enum value in a `Dict[str, Tab]` whose keys are DPG tag strings (e.g. `"global.tab.main"`). The key never matches, so the `match` always falls through to `case _: return None`. Consequence: `PlaybackRouter` never resolves a player, making all keyboard play/pause/stop shortcuts silently no-ops.
  Fix: replace with `match self.get_current_tab():` — `get_current_tab()` already returns the `Tab` value.

* **`application.py:169` — `Application` accesses a private method of `ReconstructionCoordinator`.**
  `on_reconstruction_loaded=self._reconstruction_coordinator._on_loaded` crosses the encapsulation boundary by reaching into a coordinator's private callback. `ReconstructionCoordinator` should expose a public API for this wiring (e.g. accept the callback as a constructor parameter, or expose a dedicated registration method).

* **`shell.py:314–328` — `ApplicationShell` directly holds and calls a `ReconstructionManager`.**
  `restore_current_items(reconstruction_manager: ReconstructionManager)` makes the UI shell call `reconstruction_manager.load_reconstruction()` directly, bypassing the coordinator layer. The shell is UI infrastructure and must not have domain-manager dependencies. Reconstruction restoration should be triggered via a callback passed to the shell.

* **`coordinators/reconstruction.py:148` — bare `except Exception` with a TODO comment.**
  The save error handler catches `Exception` without specifying the expected exception type, which the coding guidelines prohibit. The correct exception(s) raised by the underlying serialisation call should be identified and caught explicitly.

* **`application.py:204` — two-phase initialisation of `SequencerTabCoordinator`.**
  `self._sequencer_tab.on_edit_sample_requested = self._edit_project_sample` is set after the constructor returns, creating a window in which the coordinator is live but the callback is `None`. Every other coordinator receives its callbacks as constructor keyword arguments. `SequencerTabCoordinator` should accept `on_edit_sample_requested` in its constructor instead.

* **`coordinators/main.py:293` — `MainTabCoordinator` exposes `converter_logic` as a public property.**
  `Application` uses this to wire four callbacks (`on_load_file`, `on_load_directory`, `on_cancelled`, `generate_library`) that belong inside `MainTabCoordinator.__init__`. Exposing the internal `ConverterLogic` object breaks the coordinator's encapsulation. These four callbacks should be injected into `MainTabCoordinator` at construction time, matching the pattern used by all other coordinators.
