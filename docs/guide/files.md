# Where your files live

_SampleToNES_ keeps your work in a **SampleToNES** folder inside your documents
folder:

- Windows: `C:\Users\<you>\Documents\SampleToNES`
- macOS: `/Users/<you>/Documents/SampleToNES`
- Linux: `/home/<you>/Documents/SampleToNES`

Inside it:

- `instructions/` — the generated [instruction libraries](../formats/instruction-libraries.md) (`.ins`)
- `reconstructions/` — saved [reconstructions](../formats/reconstructions.md) (`.stn`)
- `projects/` — saved [projects](../formats/projects.md) (`.stp`)
- `config.json` — your generation [configuration](configuration.md)

You can point the library and output folders elsewhere from the **Main** tab's
**Advanced settings**, or from the right-click menu in its **Filesystem** browser.

## File types

| Type | What it is | Where it lives |
| --- | --- | --- |
| `.ins` | [instruction library](../formats/instruction-libraries.md) | `instructions/` |
| `.stn` | [reconstruction](../formats/reconstructions.md) | `reconstructions/` |
| `.stp` | [project](../formats/projects.md) | `projects/` |
| `.fti` | FamiTracker instrument (exported) | wherever you choose |
| `.ftm` | FamiTracker module (exported) | wherever you choose |

The `.fti` and `.ftm` files are what you load into
[FamiTracker](../formats/famitracker.md); the other three are _SampleToNES_'s own
formats.
