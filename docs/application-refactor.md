# Plan: Constants → YAML Configuration Refactor

## Context

The application has grown a large set of Python constants across 8 domain files covering UI tags, labels, messages, dimensions, colors, and behavioral values. These are mixed together without a clear policy distinguishing what should stay code vs. live in config. The prototype module already demonstrates the target architecture (YAML layout config + `.lang` files + Pydantic models + a `LanguageManager`), but this pattern hasn't been applied to the main application. The goal is to extend that pattern app-wide, establish a naming policy for what stays in code, separate layout/language from user-configurable settings, and clarify config ownership.

---

## Decision: What Stays as Constants?

After the refactor, Python constants (`constants/`) hold **only DearPyGUI widget identifiers**:

| Prefix | Meaning | Stays? |
|--------|---------|--------|
| `TAG_` | DearPyGUI widget tags | **Yes** — required at widget-creation time |
| `SUF_` | Suffix fragments for composing tags programmatically | **Yes** — same reason |
| `LBL_` | Display text | **No** → language YAML |
| `MSG_` | Status/error messages | **No** → language YAML |
| `TTL_` | Window/dialog titles | **No** → language YAML |
| `TPL_` | Format templates (`{}` placeholders) | **No** → language YAML |
| `DIM_` | Pixel dimensions | **No** → layout YAML |
| `COL_` | RGBA color tuples | **No** → layout/theme YAML |
| `VAL_` layout | Window defaults, padding, font sizes | **No** → layout YAML |
| `VAL_` behavior | Priority levels, delay timings, FPS interval | **No** → behavior config YAML |
| `VAL_` text | `"expand"`, `"on"`, `"off"` etc. | **No** → language YAML |

---

## Point 1: Tag Naming Policy

### Proposed convention

```
TAG_<MODULE>_<WIDGET_TYPE>[_<DETAIL>]
```

- **MODULE** maps to feature area: `MAIN`, `RECONSTRUCTIONS`, `SEQUENCER`, `INSTRUCTIONS`, `PLAYER`, `GRAPH`, `SETTINGS`, `DIALOG`, `GLOBAL`
- **WIDGET_TYPE** is the DearPyGUI element kind: `WINDOW`, `PANEL`, `TREE`, `TABLE`, `BUTTON`, `INPUT`, `SLIDER`, `THEME`, `FONT`, `MENU`, `COMBO`, `TAB`, `PROGRESS`, `TEXT`
- **DETAIL** (optional) distinguishes multiple instances of the same type in the same module

Examples of renames required:
- `TAG_PANEL_MAIN` → `TAG_MAIN_PANEL`
- `TAG_TREE_EXPLORER` → `TAG_MAIN_TREE_EXPLORER`
- `TAG_THEME_DEFAULT` → `TAG_GLOBAL_THEME_DEFAULT`
- `TAG_FONT_BOLD_NORMAL` → `TAG_GLOBAL_FONT_BOLD_NORMAL`
- `TAG_WINDOW_MAIN` → `TAG_GLOBAL_WINDOW_MAIN`

For suffixes (`SUF_`): keep as-is since they're composited programmatically and aren't directly used to address widgets.

---

## Point 2: Language System

### Extend the prototype's existing system to the full app

The prototype already has:
- `text/abstract.py` — `AbstractElement (StrEnum)`
- `text/hierarchy.py` — `Page`, `Panel`, `TextType`, `Tab` enums (already has Main, Reconstructions, Sequencer, Instructions entries)
- `text/key.py` — `TextKey` NamedTuple → dot-notation string
- `text/manager.py` — `LanguageManager` loads YAML, resolves `TextKey`

**Required additions:**

1. Add `Panel` enum values for each feature area's sub-components (Explorer, Config, Converter, Browser, Details, etc.)
2. Add `Element` subclasses for each module under `text/elements/` (currently only prototype has `prototype/text/elements.py`):
   - `text/elements/main.py`
   - `text/elements/reconstructions.py`
   - `text/elements/sequencer.py`
   - `text/elements/instructions.py`
   - `text/elements/player.py`
   - `text/elements/settings.py`
   - `text/elements/global_.py` (dialogs, menus, shared text)
3. Create `config/lang/en.yaml` (using `.yaml`; the `.lang` extension is a cosmetic choice — both work, decide at implementation time) containing all moved `LBL_`, `MSG_`, `TTL_`, `TPL_`, and the text-type `VAL_` values. Format already established by the prototype's `en.yaml`.

**Language manager ownership:** A single `LanguageManager` instance is created in `Application.__init__()` and injected into coordinators alongside config managers. It is **not** part of `ApplicationConfig`.

---

## Point 3: Paths Module and Config Directory

### `paths.py` — single source of path truth

Create `src/sampletones_application/paths.py`:
- Re-export `CONFIG_PATH`, `APPLICATION_CONFIG_PATH`, `LIBRARY_DIRECTORY`, `OUTPUT_DIRECTORY` from `sampletones_core`
- Add application-level paths: path to the `config/` directory at project root, paths to layout YAML files, path to the language file

```python
# src/sampletones_application/paths.py
from sampletones_core.constants.paths import CONFIG_PATH, APPLICATION_CONFIG_PATH, LIBRARY_DIRECTORY, OUTPUT_DIRECTORY
from pathlib import Path

CONFIG_DIRECTORY = Path(__file__).parents[3] / "config"   # project root / config
LAYOUT_DIRECTORY = CONFIG_DIRECTORY / "layout"
LANG_DIRECTORY = CONFIG_DIRECTORY / "lang"
LANG_EN = LANG_DIRECTORY / "en.yaml"
```

No module should define its own path constants — all imports go through `paths.py`.

### `config/` directory at project root

```
SampleToNES/
  config/
    layout/
      general.yaml        ← DIM_, COL_, layout VAL_ from general.py
      graphs.yaml         ← from graphs.py
      instructions.yaml   ← from instructions.py
      main.yaml           ← from main.py
      player.yaml         ← from player.py
      reconstructions.yaml← from reconstructions.py
      sequencer.yaml      ← from sequencer.py
      settings.yaml       ← from settings.py
    behavior/
      general.yaml        ← priority levels, delay timings, FPS interval, max_workers default
    lang/
      en.yaml             ← all text (LBL_, MSG_, TTL_, TPL_, text VAL_)
  src/
    ...
```

---

## Point 4: Pydantic Config Classes for Layout

Following the prototype's pattern exactly (`layout.py`, `constraints.py`, `prototype.py`, `loader.py`):

### File structure under `src/sampletones_application/layout/`

```
layout/
  __init__.py
  general.py          ← GeneralLayout (WindowLayout, PanelLayout, FontSizes, PaddingConfig, ColorTheme…)
  graphs.py           ← GraphsLayout
  instructions.py     ← InstructionsLayout
  main.py             ← MainLayout
  player.py           ← PlayerLayout
  reconstructions.py  ← ReconstructionsLayout
  sequencer.py        ← SequencerLayout
  settings.py         ← SettingsLayout
  config.py           ← LayoutConfig (root aggregating all above)
  loader.py           ← load_layout_config(layout_dir: Path) -> LayoutConfig
```

### Design rules for Pydantic models

- All models are `BaseModel` (not frozen, since layout won't be mutated at runtime — but not enforced to match prototype style)
- **No Python-level defaults** on fields. YAML is the single source of truth for defaults. Models are validated on load; missing fields raise `ValidationError`.
- Exception: fields that can legitimately be `None` (e.g. a width of `-1` meaning "fill") may default to `None`
- Colors: represent as `tuple[int, int, int, int]` or a small `RGBA` named tuple — do NOT use arbitrary strings

Example for general layout:
```python
class WindowLayout(BaseModel):
    width: int
    height: int
    x: int
    y: int
    fullscreen: bool

class PanelLayout(BaseModel):
    left: int
    right: int

class GeneralLayout(BaseModel):
    window: WindowLayout
    panels: PanelLayout
    fonts: FontSizes
    status_bar: StatusBarLayout
    dialogs: DialogsLayout
    colors: GeneralColors
```

---

## Point 5: Responsibility Separation

### Current state

`ApplicationConfigManager` conflates two concerns:
- **Application state** (which tab is open, which reconstruction is loaded) — auto-saved/restored, changes during normal use
- **Application config** (audio device, paths, window geometry) — explicitly set by user

### Proposed separation

**`ApplicationState`** (new class, extracted from `GUIState`):
- `current_tab: str`
- `current_reconstruction: Optional[Path]`
- `advanced_settings: bool`
- `autoplay: bool`
- Persisted to `sampletones.yaml` under `state:` key (currently embedded in `GUIState`)

**`ApplicationConfig`** (refined — keep `AudioConfig`, `WindowState`, `LastPaths`, `Favorites`):
- Audio device selection, buffer size, volume
- Window geometry (treated as auto-saved preference, not explicit user config)
- Last-used directories
- Favorites set

**`ApplicationConfigManager`** is renamed to **`SessionManager`** (or kept as-is with clear docstring delineation) and simply owns both:
```python
class SessionManager:
    config: ApplicationConfig   # user-controlled settings
    state: ApplicationState     # auto-managed session state
```
The separation is primarily logical/conceptual — both are still persisted to the same YAML file, but under distinct top-level keys (`config:` vs `state:`).

### New config owners (NOT in ApplicationConfig)

| Config | Owner | Loaded by |
|--------|-------|-----------|
| `LayoutConfig` | `LayoutConfigLoader` (simple function, no class needed) | `Application.__init__()` |
| `LanguageManager` | `LanguageManager(path)` | `Application.__init__()` |
| Domain config | `ConfigManager` (unchanged) | `Application.__init__()` |
| Session/app config | `SessionManager` (renamed/clarified) | `Application.__init__()` |

`Application` becomes the composition root: it creates all four and injects them into coordinators as needed.

---

## Implementation Order

1. **Tag audit + rename** — update `constants/*.py` files, update all usages site-wide (grep-driven)
2. **`paths.py`** — create module, update all import sites
3. **`config/` directory + YAML files** — extract constants into YAML; no code changes yet
4. **`layout/` Pydantic models** — create models + loader; no constants removed yet
5. **Wire layout into app** — load `LayoutConfig` in `Application.__init__()`, thread into panels/coordinators replacing constant references
6. **Language elements** — add `text/elements/*.py` for each module
7. **`config/lang/en.yaml`** — extract all text constants
8. **Wire `LanguageManager` into app** — replace `LBL_`/`MSG_`/`TTL_`/`TPL_` references with `LanguageManager` lookups
9. **`ApplicationState` extraction** — split `GUIState`, update `SessionManager`
10. **Delete emptied constants** — remove files once all references are migrated; keep `constants/*.py` files that only contain `TAG_`/`SUF_` values

---

## Verification

- `python -m py_compile src/sampletones_application/**/*.py` — no syntax or import errors
- `pytest` (existing test suite) — must stay green
- Launch app, open each tab, confirm layout is correct (dimensions, colors match current behavior)
- Open and close audio settings dialog — confirm audio config still saves/restores
- Restart app — confirm last tab and last reconstruction are restored
- Open reconstruction with a missing file — confirm error message comes from language YAML
- Check `~/.config/SampleToNES/sampletones.yaml` structure reflects `config:` / `state:` split
