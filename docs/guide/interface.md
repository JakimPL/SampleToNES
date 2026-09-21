# The interface

_SampleToNES_ has four tabs. Use `F1` to `F4` to switch between them:

- [**Main**](converting.md) (`F1`) — turn audio files into [reconstructions](../concepts/reconstruction.md).
- [**Reconstruction**](reconstruction.md) (`F2`) — listen to a reconstruction, edit its instruments, and export it.
- [**Sequencer**](sequencer.md) (`F3`) — arrange reconstructions into a song.
- [**Instructions**](converting.md#building-a-library-yourself) (`F4`) — build and browse the [instruction library](../concepts/instruction-library.md) a conversion uses.

You usually work through the tabs in this order. Convert your files on **Main**. When the conversion finishes, click **Load** to open the result on **Reconstruction**. From there, **Add to Sequencer** adds the reconstruction to a song.

The **Instructions** tab is optional. Use it to explore single [instructions](../glossary.md#instruction), the smallest sounds the chip makes.

## The menus

Each menu covers one kind of work. The lower half of **Edit** acts on what you have selected. **Voice**
acts on the voice you selected. **Reconstruction** acts on the reconstruction you have open.

Two items are easy to miss:

- **View ▸ Show advanced settings** shows the **Advanced settings** card on the **Main** tab. It has options you rarely need: how the audio is analyzed, the number of workers, and the library and output folders. [Configuration](configuration.md) explains each one.
- **Playback ▸ Audio settings...** chooses the device, sample rate, and buffer size you listen through. These differ from **Sample rate** and **NES frequency** on the **Main** tab, which set how the audio is converted.

Project properties belong to a project and are covered in the [sequencer guide](sequencer.md).

## Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists everything you can do from the keyboard and lets you change any shortcut. Click an action's shortcut and press the keys you want. If another action already uses those keys, the app names that action and asks whether to reassign them.

**Reset to defaults** restores the original shortcuts. Your changes take effect when you click **OK**, and the app keeps them for the next time you start.

`Space` plays and pauses, and `Esc` stops. On macOS, the shortcuts use Command where other platforms use Control.
