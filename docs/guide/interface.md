# The interface

_SampleToNES_ has four tabs. Use `F1` to `F4` to switch between them:

- [**Main**](converting.md) (`F1`) — turn audio files into [reconstructions](../concepts/reconstruction.md).
- [**Reconstruction**](reconstruction.md) (`F2`) — listen to a reconstruction, edit its instruments, and export it.
- [**Sequencer**](sequencer.md) (`F3`) — arrange reconstructions into a song.
- [**Instructions**](converting.md#building-a-library-yourself) (`F4`) — build and browse the [instruction library](../concepts/instruction-library.md) a conversion uses.

<div align="center">
    <img src="../images/guide/interface/tabs.webp" alt="The menu bar, the play controls and the four tabs" width="639">
</div>

You usually work through the tabs in this order. Convert your files on **Main**. When the conversion finishes, click **Load** to open the result on **Reconstruction**. From there, **Add to Sequencer** adds the reconstruction to a song.

The **Instructions** tab is optional. Use it to explore single [instructions](../glossary.md#instruction), the smallest sounds the chip makes.

## The menus

A few menu items are easy to miss:

- **View ▸ Show advanced settings** adds the **Advanced settings** card to the **Main** tab. See [Configuration](configuration.md).
- **Playback ▸ Audio settings...** sets the device you listen through. Its sample rate is separate from **Sample rate** on the **Main** tab, which sets how audio is converted.
- **Playback ▸ MIDI settings...** (`Ctrl+M`, `Cmd+Shift+M` on macOS) chooses your [MIDI keyboard](#midi-keyboard).
- **Help ▸ Documentation** opens this guide in your web browser, from a copy that comes with the app.

Project properties belong to a project and are covered in the [sequencer guide](sequencer.md).

## MIDI keyboard

A MIDI keyboard plays the voice open on **Reconstruction** and enters notes in the
[sequencer](sequencer.md#typing-a-pitch). Plug it in and choose it from **MIDI input** in **Playback ▸ MIDI settings...**. Press **Refresh** when the list misses it. The dialog shows the last key you played, so you can check the keyboard before you keep it.

With **Velocity sets the volume** on, a key struck harder sounds louder, and the sequencer writes that
volume with the note. The triangle channel plays at full volume. A sustain pedal holds the notes you have let go.

## Keyboard shortcuts

**View ▸ Keyboard shortcuts...** (`Ctrl+K`) lists every shortcut and lets you change any of them. Click a shortcut and press the keys you want. If another action already uses those keys, the app asks before reassigning them. **Reset to defaults** restores the original shortcuts.

On macOS, the shortcuts use Command where other platforms use Control.
