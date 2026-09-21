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

| Type | What it is |
| --- | --- |
| `.ins` | [instruction library](../formats/instruction-libraries.md) |
| `.stn` | [reconstruction](../formats/reconstructions.md) |
| `.stp` | [project](../formats/projects.md) |
| `.fti` | FamiTracker instrument |
| `.ftm` | FamiTracker module |
| `.json` | Bitphase instrument preset |
| `.btp` | Bitphase project |
| `.nsf` | [NSF program](../formats/nsf.md) |

The first three are your own work, saved in the folders above. The rest are exports, and the save
dialog asks where each one goes. [FamiTracker](../formats/famitracker.md) opens `.fti` and `.ftm`,
[Bitphase](../formats/bitphase.md) opens `.json` and `.btp`, and an `.nsf` plays in an NSF player or
on a NES.

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
