# The interface

_SampleToNES_ has four tabs. Use `F1` to `F4` to switch between them:

- [**Main**](converting.md) (`F1`) — turn audio files into [reconstructions](../concepts/reconstruction.md).
- [**Reconstruction**](reconstruction.md) (`F2`) — listen to a reconstruction, edit its instruments, and export it.
- [**Sequencer**](sequencer.md) (`F3`) — arrange reconstructions into a song.
- [**Instructions**](converting.md#building-a-library-yourself) (`F4`) — build and browse the [instruction library](../concepts/instruction-library.md) a conversion uses.

You usually work through the tabs in this order. Convert your files on **Main**. When the conversion finishes, click **Load** to open the result on **Reconstruction**. From there, **Add to Sequencer** adds the reconstruction to a song.

The **Instructions** tab is optional. Use it to explore single _instructions_: the smallest sounds the NES sound chip makes.

## The menus

Each menu covers one kind of work, and three of them follow what you are doing: the lower half of
**Edit** holds commands for whatever you have selected, **Voice** holds commands for the voice you
selected, and **Reconstruction** acts on the reconstruction you have open.

Two items are easy to miss:

- **View ▸ Show advanced settings** shows the **Advanced settings** card on the **Main** tab. It contains the generation method, feature scaling, worker count, and library and output folders. [Configuration](configuration.md) explains each one.
- **Playback ▸ Audio settings...** chooses the device, sample rate, and buffer size you listen through. **Sample rate** and **NES frequency** on the **Main** tab are different settings: they set how the audio is converted.

Project properties belong to a project and are covered in the [sequencer guide](sequencer.md).

## Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists everything you can do from the keyboard and lets you change any shortcut. Click an action's shortcut and press the keys you want. If another action already uses those keys, the app names that action and asks whether to reassign them.

**Reset to defaults** restores the original shortcuts. Your changes take effect when you click **OK**. They are saved with your settings and are still there the next time you start.

`Space` plays and pauses, and `Esc` stops. On macOS, the shortcuts use Command where other platforms use Control.
