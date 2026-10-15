# MIDI Input

This document describes how a MIDI keyboard is read and where its keys go. Consult it when adding a place a key plays or writes in, when changing how a port is chosen or kept, or when reaching another MIDI library. Principle 16 of [`architecture.md`](../architecture.md) states the dispatcher's contract, and [Playback](playback.md) states what a key played live sounds like.

---

## One seam over every MIDI library

Each platform reaches MIDI through its own service, so each has a library of its own: the ALSA sequencer through `alsa-midi` on Linux, and PortMidi through `pygame-ce` on Windows and macOS. Both stand behind one protocol, `MidiInputBackend` (`utils/midi/backends/`), which carries what every MIDI library offers:

- A port is named by its name, and only its backend reads its address.
- The backend hands over complete MIDI 1.0 messages as bytes, from a thread of its own, in the order they arrived. Parsing them is the application's (`utils/midi/messages.py`), so a key means the same whichever library delivers it.
- A port going away is told once, and closing a port returns once its messages stop.
- A library's failure arrives as `MidiPortError`.

Each library is imported by one module, which the import-boundary check holds. A stand-in for that module drives the backend's thread and lifecycle on every platform, and one conformance suite holds every backend to the protocol, the screen tier's stand-in included. Each backend names the quirks of its library. [Dependencies](../release/dependencies.md#midi-input) explains the choice of libraries.

## The manager reads one port by its name

`MidiInputManager` (`utils/midi/manager.py`) reads one port at a time and finds it by its name in a fresh listing, so the session keeps the name and a keyboard unplugged for one run is looked for again in the next. A refresh is a disconnection, a listing and a connection by the same name.

**A port settles before its keys count.** A device keeps what is played while nothing reads it and sends it all as a port opens, so the messages arriving within `MIDI_SETTLE_SECONDS` of an opening are dropped.

**No key is left hanging.** Whenever the keys stop arriving, as a port changes, goes away or is let go, the listener hears every key let go and the pedal come up.

## The router hands each key to one scope

`MidiRouter` (`utils/midi/router.py`) offers a key to the active scopes from the highest priority to the lowest, as the keyboard's router does. The render thread publishes the active scopes once a frame. A key lifted reaches the scope that took its press, and the pedal reaches the sound alone. A scope is called on the thread the key arrived on, so one that sounds acts at once, and one that changes the interface posts its work to the render thread.

## The coordinator owns the keyboard

`MidiCoordinator` (`coordinators/midi.py`) is the manager's listener and the owner of the MIDI settings dialog.

- **The library loads off the render thread.** As the application starts, a thread of its own loads the library, and then reads the port the session kept, where the reader picked none meanwhile. A port absent this run is left unread without a word.
- **A port picked in the dialog is read at once.** The dialog is a scope ranked as a modal, which names each key played, so the reader tries a keyboard before keeping it. OK keeps the port and the velocity setting in the session, and Cancel reads again the port the dialog opened with.
- **A keyboard going away is told on the status bar.** The session keeps its name, so the next start reads it again, and the reader picks it again in the dialog to read it sooner.
- **The teardown lets the keyboard go before playback stops**, so the sound hears every key let go.

## Who governs what

| Concern | Owner |
|---------|-------|
| What a MIDI message means | `parse_message` (`utils/midi/messages.py`) |
| What every MIDI library is held to | `MidiInputBackend`, `MidiPort`, `MidiSink` (`utils/midi/backends/protocol.py`) |
| The ALSA sequencer, through `alsa-midi` | `AlsaMidiBackend` and `AlsaMidiLibrary` (`utils/midi/backends/alsa/`) |
| PortMidi, through `pygame-ce` | `PortMidiBackend` and `load_portmidi` (`utils/midi/backends/portmidi/`) |
| The backend each platform reads | `select_midi_backend` (`utils/midi/selection.py`) |
| The port read, its settling, and the keys let go | `MidiInputManager` (`utils/midi/manager.py`) |
| Which scope takes a key | `MidiRouter` (`utils/midi/router.py`) |
| The port kept, the dialog, and a keyboard going away | `MidiCoordinator` (`coordinators/midi.py`) and `MidiConfig` (`config/session/application/midi.py`) |
