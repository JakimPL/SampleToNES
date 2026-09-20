# Configuration Organization

_SampleToNES_ ships its configuration as a YAML data package, `sampletones_config`. This
document states the principles that decide where a configuration value belongs and how it
is read; use it as the reference when adding or moving a value. It sits alongside
`docs/development/architecture.md` (application layering and ownership) and
`docs/development/guidelines.md` (coding rules).

"Configuration" names three separate things in this codebase. This document governs the
first:

- **Shipped configuration** — the `sampletones_config` YAML package: layout, theme,
  palettes, keybindings, language, behavior, deployment, and the import boundaries.
  *(This document.)*
- **Runtime user preferences** — mutable state persisted to the user profile
  (`sampletones_application/config`, e.g. `PlaybackConfig`, `ShortcutsConfig`,
  `ApplicationState`), governed by that package.
- **Project generation settings** — JSON stored beside a project
  (`sampletones_core/configs`, `config.json`), documented in
  `docs/formats/configuration.md`.

---

## Principles

### 1. Data and meaning are separate

`sampletones_config` carries values; the schema that interprets them lives in the package
that reads them. The dependency runs one way — a consumer imports the data package only to
resolve its directory (`CONFIG_DIRECTORY`), and the package itself is pure YAML with an
empty `__init__.py`. Each schema lives with its reader:

- `sampletones_application` owns the layout, theme, palettes, keybindings, language,
  behavior, and deployment schemas.
- `sampletones_tools` owns the import-boundary schemas.
- `sampletones_shared` owns the loader primitives (`load_yaml_model`, `load_yaml_model_dir`).

So the data carries the values and the consumer carries the meaning, and the two evolve
on their own terms.

Data a package reads ships with that package, beside the schema reading it: the matching
defaults every reconstruction starts from sit in `sampletones_core/configs/generation.yaml`,
the calibration tuning in `sampletones_tools/calibration/config/`, the synthetic corpus in
`sampletones_tools/corpus/config/` and the application mark in `sampletones_tools/assets/mark/config/`,
each placed by `package_directory`. `sampletones_config`
holds what the application reads and the import boundaries, which state the repository's
package layers for every tree and which [package layers](../packages.md) refers to.

### 2. The top level is organized by domain

`sampletones_config` has one top-level directory per schema family and its loader:
`application`, `behavior`, `boundaries`, `keybindings`, `lang`, `layout`,
`palettes`, `theme`. Each domain owns its schema and its load path (see
[Domains](#domains)). A new domain is a new top-level directory with its own schema owner
and loader.

Palettes are a domain of their own because two other domains resolve against them: a color
field in `layout/` and a color entry in `theme/` both name a palette token, and the palette
is what turns that name into a value. A directory holds one file per palette, named after the
palette it declares, and every palette answers the same token set — an entry names one token
and each palette must have an answer for it.

Keybindings are a domain on the same shape: a scheme is a named set a preference selects by
name, so the directory holds one file per scheme, named after the scheme it declares, and
every scheme answers the same action set — an entry names one `ShortcutId` and each scheme
must have a combination for it. What the directory carries is the combinations, which are a
reader's to choose; the actions and the categories are code ([`keyboard.md`](keyboard.md)).

### 3. The config tree mirrors the code

The layout config is shaped like the code that reads it: its directory tree matches the
`LayoutConfig` model tree, which mirrors the application's feature-area taxonomy across
`ui/panels/`, `logic/`, and `view_model/`. A value's place in the config therefore
predicts its place in the code. Three conventions keep the mirror true:

- **A feature area is a directory of fragments.** Each area is a directory loaded by
  `load_yaml_model_dir`; every `<field>.yaml` supplies the model's `<field>`, and an
  optional `root.yaml` carries the loose scalars that own no section file. Two
  cross-cutting resources — `fonts.yaml` and `glyphs.yaml` — are single self-contained
  files at the `layout/` root, each one resource in one file.
- **File stem = field = model.** `choice.yaml` fills field `choice`, validated by
  `ChoiceLayout` in `choice.py`; the three names match within a domain, so one name traces
  a value from YAML through field to schema. A stem is unique within its domain: the same
  name may recur across domains as a related-but-distinct resource
  (`layout/general/plus_minus_buttons.yaml` sizes a widget while
  `theme/plus_minus_buttons.yaml` styles it — one widget, two domains, loaded separately).
- **Tabs sit where their coordinators sit.** The four notebook tabs live under
  `layout/tabs/` (`main`, `instructions`, `reconstruction`, `sequencer`), matching
  `coordinators/tabs/` and aggregated as `LayoutConfig.tabs`; a tab's configuration is
  found where its code is. Cross-tab and shared areas stay at the `layout/` root as their
  own feature areas: `general/`, the plot-element family `graphs/`, the transport toolbar
  `player/`, and the dialogs `project_properties/` and `settings/`.

### 4. Every value has one home

A value lives in exactly one place, owned by the concept it describes. A tab's own
geometry — width and height together — lives in that tab's directory. The shared outer
column skeleton (`side`, `center_weight`) lives in `general/`, since it belongs to every
tab equally. The values that drive responsive resizing (`baseline_viewport_width`,
`baseline_viewport_height`, the graph-stack cap) live together in `general/responsive.yaml`
because they are the input to one scheme. Ownership decides the home: whoever owns the
concept holds the value, and it appears once.

### 5. Storage shape and consumer shape differ

Principles 1–4 shape the config for **where a value is authored**. What a consumer needs
is often a different shape, and the two are reconciled at the composition root
(`Application.__init__`, where the validated `LayoutConfig` already exists). Each consumer
receives a view built for it:

- A **feature consumer** — a panel or UI element — receives its model whole:
  `GUIConverterPanel(layout: ConverterLayout)`. The model carries all of that panel's own
  geometry, so a new field reaches the panel through the model it already holds.
- A **generic primitive** — the responsive math (`expanded_side_width`,
  `stacked_graph_height`), the column builders (`ColumnSpec`, `TabColumns`), raw
  `dpg.configure_item` — receives the plain integers it computes with, since it blends a
  config value with a live runtime measurement (e.g. `dpg.get_viewport_client_width()`)
  and works below the level of any layout model.
- A **tab coordinator** receives a per-tab view. A frozen-dataclass DTO in the
  `parameters/` package gathers exactly what one tab needs: the shared six-field
  `TabGeometry` core, the flat integers its primitive sinks consume, and the cohesive
  feature models it forwards whole (`SchedulingBehavior`, `GraphsLayout`, the tab's own
  `<Tab>Layout`, the color blocks). A small factory produces any narrowed slice a consumer
  needs (`TreeColors.create`, `PitchStepperStyle.from_general`).

The type signals which side of the boundary a value is on: a frozen Pydantic model with
`extra="forbid"` is a YAML fragment; a `@dataclass(frozen=True)` is a view derived in code.
The composition root is the one place that knows both shapes, so each deep path from
storage to consumer is written once, in one factory. This is what the DTO layer is for: a
coordinator depends only on the narrowed view handed to it, and the knowledge of where
each value sits in the tree stays in the factory.

---

## Domains

Each domain is one top-level directory with one schema owner and one load path.
`sampletones_config/README.md` lists the directories and the schema owning each, beside the data
itself.

The palettes load first, and the source holding the active one is injected as validation **context**,
so any color field in layout or theme keeps the token it was written as and reads its value from the
palette in place when it is drawn with. `PaletteCatalog` names the palette a preference selects and
answers with the shipped default for a name the build does not carry, so a preference outlives the
build that wrote it. `ShortcutCatalog` answers the same way for a keybinding scheme; how a scheme is
validated, layered under a reader's own rebindings and chosen per platform is
[`keyboard.md`](keyboard.md).

Layout and theme schemas are `frozen=True, extra="forbid"`, and loading is eager at the composition
root, wrapped as `SystemError`, so a mismatch between YAML and schema surfaces loudly at startup.

Behavior loads as its own domain — its own directory, schema owner and load call — and attaches to the
layout result as `LayoutConfig.behavior`, so every consumer reaches it as `layout.behavior.*` through
one access path.

Boundaries is the domain a developer tool reads rather than the application. It states the layer graphs
the packages divide into, the imports each part of the application stays clear of, the spellings a tree
keeps out, and the standard-library rule the bootstrap scripts hold to. A declaration draws on the
named prefix groups `general.yaml` holds, so a set several rules reach for is written once, and a name
reaching no group is refused as the domain is read. [Package layers](../packages.md) states what the
graphs mean.

---

## Loading

Three load mechanisms serve the three grouping schemes:

- **Field aggregation** (layout, and every domain that mirrors the code). The config is built field by
  field — one file per field, one directory per feature area — so the directory structure and the model
  structure stay identical (principle 3), validated strictly with `extra="forbid"`.
- **Tag-graph discovery** (theme). Theme is grouped by the widget family it styles, for a person
  navigating it, while the load meaning is carried by each spec's `tag` and `extends`: every file under
  `theme/` is read, validated, resolved against its parent and registered by tag. Every theme extends
  the base unless it names another parent.
- **Name-keyed discovery** (palettes, keybindings). Every file in the directory is read and indexed by
  the name it declares, with each file's stem held against that name, so one name traces a palette or a
  scheme from a stored preference to the file on disk.

Deployment and the boundaries each load through a `.load()` classmethod of their own, over the same
low-level primitives in `sampletones_shared/utils/serialization.py` — the one module that calls
`yaml.safe_load`.
