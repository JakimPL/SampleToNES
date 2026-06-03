Here's the comprehensive plan based on your answers and my analysis:

---

## Plan: SampleToNES Codebase Reorganization

**TL;DR**: Split the monolithic sampletones package into four focused packages, then clean up the app layer in two design-focused phases. Phases 1–3 are mechanical (move code, update imports), Phases 4–5 are design changes. Each phase is independently reviewable and the app runs after every phase.

---

### Target package structure

```
src/
  sampletones/           ← thin entry point only (__main__.py)
  sampletones_shared/    ← meta, types, exceptions, logger, domain-free utils
  sampletones_core/      ← domain: audio, fft, generators, instructions,
                            library, reconstructions, sequencer, exporters,
                            configs, data, structures, constants, parallelization
  sampletones_application/
    ui/                  ← DPG rendering only: panels, elements, themes, resources
    logic/               ← DPG-free: library manager, reconstruction manager,
                            browser, player, regenerator, feature data
    config/              ← ConfigManager (cleaned), ApplicationConfigManager
    utils/               ← DPG helpers, dialogs, shortcuts, callback queue
    constants/           ← app-specific constants
  sampletones_schemas/   ← already isolated, unchanged
```

---

### Phase 1 — Extract `sampletones_shared`

**Goal**: Establish a domain-free shared infrastructure package.

**Moves from `sampletones/`:**
- `meta/`, `types/`, `exceptions/`, `logger/`
- `utils/common.py`, `utils/arrays.py`, `utils/callbacks.py`, `utils/serialization.py`, `utils/frequencies.py`, `utils/famitracker.py`, `utils/collections/`, `utils/system/`, `utils/transformations/`

**Supporting changes:**
- pyproject.toml: add `sampletones_shared` to `hatch.build.targets.wheel.packages` and `isort.known_first_party`
- Update all `from sampletones.utils/meta/types/logger/exceptions import ...` throughout `sampletones/` and `sampletones_schemas/`
- Move matching tests (utils etc.)

**Verification**: `mypy` passes on `sampletones_shared`; no `dearpygui` or domain imports inside it; all tests pass.

---

### Phase 2 — Extract `sampletones_core`

**Goal**: Pure domain package with zero GUI or app dependencies.

**Moves from `sampletones/`:**
- `audio/`, `fft/`, `ffts/`, `generators/`, `instructions/`, `library/`, `reconstructions/`, `sequencer/`, `exporters/`, `configs/`, `data/`, `structures/`, `constants/`, `array.py`, `parallelization/`, `timers/`, `tree/`, scripts

**`sampletones/` becomes**: only __main__.py + `__init__.py` (5–10 lines each).

**Supporting changes:**
- pyproject.toml: add `sampletones_core` to packages; update `mypy.files` from sampletones → `src/sampletones_core`
- Move core tests

**Verification**: `grep -r "dearpygui" src/sampletones_core/` returns nothing; all core tests pass.

---

### Phase 3 — Extract `sampletones_application` + `ui/logic` split

**Goal**: Move the application into its own package and enforce the UI/logic boundary structurally.

**Mapping of `application/` → `sampletones_application/`:**

| Current | Target |
|---|---|
| `application/panels/`, `elements/`, `themes/`, `resources/` | `ui/panels/`, `ui/elements/`, `ui/themes/`, `ui/resources/` |
| `application/instruction/`, `library/`, `player/`, `reconstruction/`, `explorer/` | `logic/instruction/`, `logic/library/`, `logic/player/`, `logic/reconstruction/`, `logic/explorer/` |
| `application/config/` | `config/` |
| `application/utils/` | `utils/` |
| `application/constants/` | `constants/` |
| `application/gui.py` | `app.py` |

**Supporting changes:**
- `sampletones/__main__.py` imports `GUI` from `sampletones_application.app`
- pyproject.toml: add `sampletones_application`; update `isort.known_first_party`

**Verification**: App starts and operates normally; `grep -r "dearpygui" src/sampletones_application/logic/` returns nothing.

---

### Phase 4 — Decouple `ConfigManager` from DPG *(design refactor)*

**Goal**: `ConfigManager` knows only `Config`; no widget tag strings.

**Current problem**: `ConfigManager.config_parameters` and `generator_tags` are dicts keyed by `TAG_CHECKBOX_...`, `TAG_INPUT_...` — the config manager knows about DPG widget IDs.

**Changes:**
- `ConfigManager` becomes: `load_config()`, `save_config()`, `set_config(Config)`, `add_change_callback()`  — no tag dicts
- Each settings panel declares its own `{DPG_TAG: (config_section, field_name)}` mapping locally
- `GUIReconstructorPanel._on_parameter_change` reads its own DPG values, builds a `Config` update via `config.model_copy(update={...})`, calls `config_manager.set_config(...)`
- `ApplicationConfigManager.save_current_tab()`: remove `dpg.get_value()` call; `GUI` passes the current tab value when calling it

**Files**: `sampletones_application/config/manager.py`, `sampletones_application/ui/panels/main/config.py`, reconstructor.py, `advanced.py`

**Verification**: `grep "TAG_" src/sampletones_application/config/manager.py` returns nothing; all config load/save flows tested.

---

### Phase 5 — Decompose the `GUI` god object *(design refactor)*

**Goal**: `GUI` becomes a thin compositor. Action logic moves to feature controllers in `logic/`.

**What moves out of `GUI`:**

| Controller (new, in `logic/`) | Action methods extracted from GUI |
|---|---|
| `ReconstructionController` | load, save, close, export WAV/FTIS, regenerate, `_on_reconstruction_loaded/closed/updated` |
| `ConversionController` | convert file/dir, cancel, progress; *also absorbs threading+ETA from `GUIConverterPanel`* |
| `LibraryController` | load library, generate, progress |
| `PlaybackController` | play, pause, stop, play-from-start, autoplay toggle |

**What `GUI` retains**: DPG context init, viewport setup, font/theme registration, panel construction, callback wiring from panels → controllers.

**`GUIConverterPanel` after refactor**: pure rendering; calls `ConversionController` methods; no `threading`, no `ETAEstimator`, no `Optional[ReconstructionConverter]` state.

**Verification**: `GUI` class < 300 lines; no `Reconstruction*` domain imports in gui.py/`app.py`; all end-to-end flows work.

---

### Relevant files (key ones)

- gui.py — becomes `sampletones_application/app.py`, then refactored in Ph.5
- manager.py — refactored in Ph.4
- converter.py — moved Ph.3, refactored Ph.5
- reconstruction.py — moved Ph.3, refactored Ph.5
- callbacks.py — moves to `sampletones_shared` in Ph.1
- pyproject.toml — updated in each package phase

---

### Further Considerations

1. **Entry point naming**: After Phase 2, the sampletones package is 2 files. Consider whether `sampletones_application.app:main` should become the script entry point directly, dropping the thin wrapper. I recommend keeping the sampletones wrapper for user-facing CLI stability (the `pyproject.scripts` entry stays `sampletones.__main__:main`).

2. **Enforcement of `ui/logic` boundary**: After Phase 3, the `logic/` → no `dearpygui` rule needs an enforcement mechanism. A simple `grep` in CI or a mypy plugin rule (e.g. a custom scripts check) would prevent regressions without adding a dependency.

3. **`CallbackQueue` placement**: Currently in `application/utils/` — it would move to `sampletones_application/utils/` in Phase 3. It has no DPG imports and is driven by frame events, making it an app-layer utility. This is correct placement. `CallbackMixin` (in `sampletones_shared`) calling `CallbackQueue` (in `sampletones_application`) is an allowed bottom-up → top-down dependency — but only if panels explicitly pass `CallbackQueue.add` as the callback invoker, which is the current pattern.
