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
| `.json` | Bitphase instrument preset (exported) | wherever you choose |
| `.btp` | Bitphase project (exported) | wherever you choose |
| `.nsf` | NES sound file (exported) | wherever you choose |

The `.fti` and `.ftm` files are what you load into
[FamiTracker](../formats/famitracker.md), `.json` and `.btp` are what
[Bitphase](../formats/bitphase.md) reads, and an `.nsf` plays on its own in a NES
sound player or on the console; the rest are _SampleToNES_'s own formats.

## Exported files

The extension names what an export is written for: `.fti` and `.ftm` go to
FamiTracker, `.json` and `.btp` to Bitphase, and `.nsf` to a NES sound player. The
save dialog offers the file types that fit what you are exporting and fills in the
extension of the type it is set to. Exporting one channel offers all three, so
switching the type there switches the target; typing an extension yourself picks it
directly.

What you name in the dialog also names what a tracker lists:

| Export | You name | What is written |
| --- | --- | --- |
| **Instruments** panel ▸ **Export instrument...** | the file | that file, its instrument carrying the name you gave |
| **Reconstruction ▸ Export instruments** | the batch | one file per channel beside that name, each named `<name> (channel)`, or a single file at that name for `.nsf` |
| **File ▸ Export** | the file | that file, holding the whole song |

So exporting a `Kick` reconstruction to FamiTracker instruments writes
`Kick (pulse1).fti`, `Kick (triangle).fti`, and one file for every other channel the
reconstruction uses, all in the folder you chose. An `.nsf` gathers every channel into
one program, so it is the single file you named.
