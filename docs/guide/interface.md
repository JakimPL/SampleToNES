# The interface

_SampleToNES_ has four tabs. Use `F1` to `F4` to switch between them:

- [**Main**](converting.md) (`F1`) — turn audio files into [reconstructions](../concepts/reconstruction.md).
- [**Reconstruction**](reconstruction.md) (`F2`) — listen to a reconstruction, edit its instruments, and export it.
- [**Sequencer**](sequencer.md) (`F3`) — arrange reconstructions into a song.
- [**Instructions**](converting.md#the-instruction-library) (`F4`) — build and browse the [instruction library](../concepts/instruction-library.md) a conversion uses.

You usually work through the tabs in this order. Convert your files on **Main**. When the conversion finishes, click **Load** to open the result on **Reconstruction**. From there, **Add to Sequencer** adds the reconstruction to a song.

The **Instructions** tab is optional. It lets you explore individual _instructions_ — the unit blocks produced by the NES sound processor.

## The menus

Each menu covers one kind of work:

- **File** — projects, exporting a song as a module or a program, and rendering a song to audio.
- **Edit** — undo and redo, followed by commands for whatever you have selected. Its lower half changes with what you are working on.
- **Reconstruction** — creating, opening, and saving reconstructions, and exporting them.
- **Voice** — adding voices to the sequencer, and commands for the voice you selected.
- **Playback** — playing, autoplay, following the song, and muting channels.
- **View** — advanced settings, favorites, the display, and the shortcuts.
- **Help** — **About**.

Two items are easy to miss:

- **View ▸ Show advanced settings** shows the **Advanced settings** card on the **Main** tab. It contains the generation method, feature scaling, worker count, and library and output folders. [Configuration](configuration.md) explains each one.
- **Playback ▸ Audio settings...** chooses the device, sample rate, and buffer size you listen through. These are separate from **Sample rate** and **NES frequency** on the **Main** tab. Those settings decide how the audio is reconstructed.

Project properties belong to a project and are covered in the [sequencer guide](sequencer.md).

## Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists everything you can do from the keyboard and lets you change any shortcut. Click an action's shortcut and press the keys you want. If another action already uses those keys, the app names that action and asks whether to reassign them.

**Reset to defaults** restores the original shortcuts. Your changes take effect when you click **OK**. They are saved with your settings and are still there the next time you start.

`Space` plays and pauses, and `Esc` stops. When you have picked out a row in the converter's list, the first `Esc` lets that row go and the next one stops playback. On macOS, the shortcuts use Command where other platforms use Control.
