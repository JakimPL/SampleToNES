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
| `.fti` | [FamiTracker instrument](../formats/famitracker.md) |
| `.ftm` | [FamiTracker module](../formats/famitracker.md) |
| `.json` | [Bitphase instrument preset](../formats/bitphase.md) |
| `.btp` | [Bitphase project](../formats/bitphase.md) |
| `.nsf` | [NSF program](../formats/nsf.md) |

The first three are your own work, saved in the folders above. The rest are exports, and the save
dialog asks where each one goes. [FamiTracker](../formats/famitracker.md) opens `.fti` and `.ftm`,
[Bitphase](../formats/bitphase.md) opens `.json` and `.btp`, and an `.nsf` plays in an NSF player or
on a NES.

## Naming exported files

The save dialog lists the file types that fit your export, and adds the extension of the type you
pick. When you export one channel, the dialog lists all three instrument types, so you can choose the
program the file is for. You can also type the extension yourself.

The name you type also names the instrument in the tracker. What the app saves depends on the export:

- **Export instrument...** in the **Instruments** panel saves one file. The name you type is the file's
  name, and the instrument inside it has the same name.
- **Reconstruction ▸ Export instruments** saves one file per channel. The name you type is the name of
  the set, and each file is named `<name> (channel)`. An `.nsf` export is one file, and its title is set
  in the **Export NSF program** window.
- **File ▸ Export** saves one file with the whole song.

For example, exporting a reconstruction named `Kick` to FamiTracker instruments saves
`Kick (pulse1).fti`, `Kick (triangle).fti`, and one file for each other channel the reconstruction
uses. An `.nsf` export saves every channel in one file.
