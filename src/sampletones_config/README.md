# `sampletones_config`

Shipped, read-only **YAML data** for _SampleToNES_. This package holds values only — it
has no schemas and no logic, and its `__init__.py` is intentionally empty. Its one
programmatic role is to be importable so consumers can resolve its directory
(`CONFIG_DIRECTORY`).

The schema that validates each file lives in the **consuming** package:

- `sampletones_application` — layout, theme, palettes, language, behavior, deployment.
- `sampletones_core` — calibration.
- `sampletones_shared` — the import boundaries and the loader primitives.

The data package must not import a schema, and a schema package must not inline data.

## Domains

| Directory | Purpose | Schema owner |
|-----------|---------|--------------|
| `application/` | Deployment-time environment knobs | `DeploymentConfig` |
| `behavior/` | Non-visual runtime behavior | `BehaviorConfig` |
| `boundaries/` | The imports the source tree is held to | `ImportBoundaryRules` |
| `calibration/` | DSP calibration tuning | `CorpusConfig`, `RefereeConfig` |
| `keybindings/` | The key combinations each named action answers | `ShortcutScheme` |
| `lang/` | Interface strings (i18n) | `LanguageManager` |
| `layout/` | UI geometry, dimensions, fonts | `LayoutConfig` |
| `palettes/` | The colour sets layout and theme resolve against | `Palette` |
| `theme/` | DearPyGui theme/colour styling | `ThemeSpec` |

The rules for where a value belongs, how the directories nest, and how each domain is
loaded are prescriptive and documented in
[`docs/development/config-organization.md`](../../docs/development/config-organization.md).
