# Configuration Organization

This document describes how _SampleToNES_ stores its configuration: the YAML data
package `sampletones_config`, the packages that hold the schemas that read it, and the
rules that decide where a configuration value belongs. It is prescriptive — the
contracts here bind every configuration file and every loader. Use it as the reference
when adding or moving a configuration value. It complements
`docs/development/architecture.md` (application layering and ownership) and
`docs/development/guidelines.md` (coding rules).

The word "configuration" is overloaded in this codebase. **This document governs the
shipped YAML package `sampletones_config` only.** Two other, unrelated things also carry
the name and are governed elsewhere:

- **Runtime user preferences** — mutable, persisted to the user profile
  (`sampletones_application/config`, e.g. `PlaybackConfig`, `ApplicationState`).
- **Project generation settings** — serialized as JSON (`sampletones_core/configs`,
  `config.json`), documented in `docs/formats/configuration.md`.

Neither lives in the YAML package, and neither is governed here.

---

## The package boundary

`sampletones_config` holds **YAML data and nothing else**. Its `__init__.py` is empty;
its only programmatic role is to be importable so consumers can resolve its directory
(`CONFIG_DIRECTORY = Path(sampletones_config.__file__).parent`, with a PyInstaller
`sys._MEIPASS` fallback for frozen builds).

The schema that validates each file lives in the **consuming** package, never in the
data package:

- `sampletones_application` owns the layout, theme, palette, language, behavior, and
  deployment schemas.
- `sampletones_core` owns the calibration schemas.
- `sampletones_shared` owns the loader primitives (`load_yaml_model`,
  `load_yaml_model_dir`), and nothing schema-specific.

This separation is a rule, not a convenience:

- The data package **must not** import a schema, and a schema package **must not** inline
  data. The three trees stay independent.
- A file's shape is therefore learned from its schema in the consuming package; the data
  package carries the values, the consumer carries the meaning.

---

## Domains

The top level of `sampletones_config` is grouped by **domain** — one directory per
schema family and its loader.

| Domain | Directory | Schema owner | How it is loaded |
|--------|-----------|--------------|------------------|
| Application | `application/` | `DeploymentConfig` (`sampletones_application/config/deployment/`) | `DeploymentConfig.load()`, with `SAMPLETONES_*` env overrides |
| Behavior | `behavior/` | `BehaviorConfig` (`sampletones_application/layout/behavior.py`) | folded into `LayoutConfig.behavior` by `load_layout_config` |
| Calibration | `calibration/` | `CorpusConfig`, `RefereeConfig` (`sampletones_core/calibration/config/`) | each model's own `.load()` |
| Language | `lang/` | `LanguageManager` (`sampletones_application/categories/`) | flat dotted-key string map |
| Layout | `layout/` | `LayoutConfig` (`sampletones_application/layout/config.py`) | `load_layout_config` (`layout/loader.py`) |
| Theme | `theme/` | `ThemeSpec` (`sampletones_application/ui/themes/spec.py`) | `ThemeLoader.load_all()` → `ThemeRegistry` |

The palette (`layout/palette.yaml` → `Palette`, `sampletones_application/utils/palette.py`)
is a layout-domain resource loaded first and then injected as validation **context**, so
any colour field in layout or theme may reference a palette token that resolves against
the one loaded palette.

Layout and theme schemas are `frozen=True, extra="forbid"` — immutable, and a rejection
of any unknown key. Because loading is eager at the composition root
(`Application.__init__` → `load_layout_config`, errors wrapped as `SystemError`), a
YAML↔schema mismatch fails loudly at startup rather than silently at use.

---

## Principles

### P1 — The top level is grouped by domain

One directory per schema family + loader: `application`, `behavior`, `calibration`,
`lang`, `layout`, `theme`. A new domain is a new top-level directory with its own schema
owner and loader.

### P2 — `layout/` mirrors the application's feature-area taxonomy

The layout tree repeats the same feature-area set the rest of the application already
uses across `ui/panels/`, `logic/`, and `view_model/`: a shared `general/` plus one
directory per tab — `main`, `instructions`, `reconstruction`, `sequencer`, `player`.
The correspondence is **1:1 in three places**: the YAML directory, the field on
`LayoutConfig`, and the tab coordinator that owns that tab's layout
(`architecture.md`: _"Tab layout is the coordinator's."_). A tab's configuration is
found where its code is found.

### P3 — A feature area is a directory of fragments

Each feature area is a directory, loaded by `load_yaml_model_dir`: every `<field>.yaml`
supplies the model's `<field>`, and a `root.yaml` holds the loose scalars that own no
section file of their own. No feature area is a single flat file.

**Exception:** atomic cross-cutting resource files — `fonts.yaml`, `glyphs.yaml`,
`palette.yaml` — stay flat at the `layout/` root. Each is a single self-contained
resource, not a feature area; a directory whose only member would be `root.yaml` adds
structure without meaning.

### P4 — Geometry belongs to its owner

The shared outer column skeleton (`side`, `center_weight`) and the responsive knobs live
in `general/`. A tab's own panel geometry — **both width and height** — lives in that
tab's directory. A single tab's dimensions are never split across a shared file and a
per-tab file.

### P5 — The responsive baseline has one home

The values that drive responsive resizing (`baseline_viewport_width`,
`baseline_viewport_height`, the graph-stack cap) live together in one `general/`
section. They are the input to one scheme and belong in one place, not scattered across
`columns`, `window`, and `graphs`.

### P6 — File stem = field name = model name

A fragment's file stem equals the Pydantic field it fills, which equals the tag `MODULE`
where one applies; the schema module is named to match. `choice.yaml` fills field
`choice` and is validated by `ChoiceLayout` in `choice.py` — no prefix drift between the
three.

### P7 — `theme/` groups by UI-element family, and this is a second scheme on purpose

Themes are grouped by the widget family they style (`button/`, `channels/`, `dialog/`,
`header/`, `nodes/`, `panel/`, `player/`, `tables/`). This differs from the layout
scheme deliberately: `ThemeLoader.load_all()` discovers every theme with a recursive
`rglob` and resolves it by its `tag` and its `extends` inheritance graph — so theme
directories are organizational for humans, and carry no load-order or structural
meaning. Every theme inherits the base `default` theme unless it names another `extends`.

---

## Loading paradigms

Two paradigms coexist by design, one per grouping scheme:

- **Layout — typed field aggregation.** `load_layout_config` builds `LayoutConfig`
  field by field: `load_yaml_model` for a single-mapping file, `load_yaml_model_dir` for
  a feature-area directory. The directory structure mirrors the model structure exactly
  (P2, P3), and validation is strict (`extra="forbid"`).
- **Theme — tag-graph discovery.** `ThemeLoader` reads every `*.yaml` under `theme/`
  recursively, validates each as a `ThemeSpec`, topologically sorts the `extends` graph,
  merges parent entries under child overrides, and registers the results in the
  `ThemeRegistry` singleton keyed by `tag`.

Palette, deployment, and calibration each expose a bespoke `.load()` classmethod
following the same low-level primitives in `sampletones_shared/utils/serialization.py`
(the one module that calls `yaml.safe_load`).

---

## Known deviations

Recorded in `docs/development/bugs-and-todos.md § Architecture` and paid off by the
configuration-reorganization phases. Until a box is checked, the current tree is out of
line with a principle above:

- [x] **P3** — `main`, `player`, `settings`, `project_properties` are flat files, not
  directories of fragments. *(Resolved: each is now a directory of fragments with a
  mirroring model package, loaded by `load_yaml_model_dir`.)*
- [ ] **P2** — there is no `reconstruction` layout section; the reconstruction tab reads
  its geometry from `general/columns.yaml` and `graphs/`. *(The section is born with its
  first fragment — `reconstruction/columns.yaml` — when geometry moves, rather than as an
  empty directory: a feature area is a directory of fragments, and it has none until
  then.)*
- [ ] **P4** — per-tab right-column widths live in the shared `general/columns.yaml`
  (`instructions_right`, `reconstructions_right`, `sequencer_right`) while the matching
  heights live in per-tab files.
- [ ] **P5** — the responsive baseline is split across `general/columns.yaml`
  (`baseline_viewport_width`), `general/window.yaml` (`min_height`), and
  `graphs/dimensions.yaml` (`max_stack_height`).
- [ ] **P6** — `instructions/choice.yaml` (field `choice`) is validated by
  `InstructionChoiceLayout`, a prefix the stem does not carry.
- [ ] **P1** — `behavior/` is its own domain yet is folded into `LayoutConfig.behavior`
  rather than owning a first-class aggregate.
- [ ] **Cleanup** — `VERSION_CONFIG_PATH` (`sampletones_application/paths.py`) points at
  a `version.yaml` that does not exist and is never read.
