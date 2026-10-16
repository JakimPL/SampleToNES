from functools import partial
from typing import Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.sequencer.keys import SequencerKeys
from sampletones_application.logic.shared.live import Keyboard, LiveKey
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_core.audio.output import Post
from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import velocity_levels


class TrackerKeys:
    """The keys of either keyboard entering notes in the tracker, each sounding the row it wrote while it is down.

    A computer key arrives on the render thread, where the grid has already entered its note, and reports the
    cell it wrote. A MIDI key arrives on the MIDI library's thread, and entering a note writes the project and
    draws the grid, so its press and its release each cross to the render thread, in the order played, and
    the release follows its press there. The press asks again whether the tracker takes notes, since the grid
    may have moved on since the frame that published the scope, and writes the volume the key was struck at
    where the MIDI settings say so.
    """

    def __init__(
        self,
        tracker: GUISequencerTrackerPanel,
        keys: SequencerKeys,
        session_manager: SessionManager,
        *,
        post: Post,
    ) -> None:
        self._tracker = tracker
        self._keys = keys
        self._session_manager = session_manager
        self._post = post

    def computer_key_entered(self, key_code: int, row_index: int, channel: Optional[ChannelName]) -> None:
        """Sounds the row a piano key entered its note on."""
        self._keys.strike(LiveKey(keyboard=Keyboard.COMPUTER, number=key_code), row_index, channel)

    def computer_key_released(self, key_code: int) -> None:
        self._keys.lift(LiveKey(keyboard=Keyboard.COMPUTER, number=key_code))

    def press(self, note: int, velocity: int) -> None:
        """Enters the note a MIDI key names on the render thread, and sounds the row it wrote."""
        self._post(partial(self._enter, note, velocity))

    def lift(self, note: int) -> None:
        self._post(partial(self._keys.lift, LiveKey(keyboard=Keyboard.MIDI, number=note)))

    def _enter(self, note: int, velocity: int) -> None:
        if not self._tracker.takes_notes():
            return

        levels = velocity_levels(velocity) if self._session_manager.velocity_sets_volume else None
        entered = self._tracker.enter_note(note, levels=levels)
        if entered is not None:
            self._keys.strike(LiveKey(keyboard=Keyboard.MIDI, number=note), entered.row, entered.channel)
