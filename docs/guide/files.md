# Where your files live

_SampleToNES_ saves your work in a **SampleToNES** folder inside your documents folder:

- Windows: `C:\Users\<you>\Documents\SampleToNES`
- macOS: `/Users/<you>/Documents/SampleToNES`
- Linux: `/home/<you>/Documents/SampleToNES`

The folder contains:

- `instructions/`: your [instruction libraries](../formats/instruction-libraries.md) (`.ins`)
- `reconstructions/`: your [reconstructions](../formats/reconstructions.md) (`.stn`)
- `projects/`: your [projects](../formats/projects.md) (`.stp`)
- `config.json`: your [configuration](configuration.md)

To use other folders for libraries and reconstructions, open **Advanced settings** on the **Main**
tab, or right-click in the **Filesystem** browser.

## File types

| Type | What it is | Where it is saved |
| --- | --- | --- |
| `.ins` | [instruction library](../formats/instruction-libraries.md) | `instructions/` |
| `.stn` | [reconstruction](../formats/reconstructions.md) | `reconstructions/` |
| `.stp` | [project](../formats/projects.md) | `projects/` |
| `.fti` | FamiTracker instrument | where you choose |
| `.ftm` | FamiTracker module | where you choose |
| `.json` | Bitphase instrument preset | where you choose |
| `.btp` | Bitphase project | where you choose |
| `.nsf` | NES sound file | where you choose |

The last five types are exports:

- Open `.fti` and `.ftm` files in [FamiTracker](../formats/famitracker.md).
- Open `.json` and `.btp` files in [Bitphase](../formats/bitphase.md).
- Play `.nsf` files in an NSF player or on a NES.

## Naming exported files

The save dialog lists the file types that fit your export, and adds the extension of the type you
pick. When you export one channel, the dialog lists all three instrument types, so you can pick the
program there. You can also type the extension yourself.

The name you type also names the instrument in the tracker:

| Export | The name you type | What the app saves |
| --- | --- | --- |
| **Instruments** panel ▸ **Export instrument...** | the file | one file, and the instrument inside it has the same name |
| **Reconstruction ▸ Export instruments** | the set | one file per channel, each named `<name> (channel)`. For `.nsf`, one file, and its title is set in the **Export NSF program** window |
| **File ▸ Export** | the file | one file with the whole song |

For example, exporting a reconstruction named `Kick` to FamiTracker instruments saves
`Kick (pulse1).fti`, `Kick (triangle).fti`, and one file for each other channel the reconstruction
uses. An `.nsf` export saves every channel in one file.
