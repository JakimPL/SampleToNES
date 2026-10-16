from typing import Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.shared.live import Keyboard, LiveKey, LiveKeysLogic, StrikeFollower
from sampletones_shared.constants.music import OCTAVE_OFFSET, OCTAVE_SEMITONES

from .arming import KeyArming


class ReconstructionKeys:
    """The keys of either keyboard playing the voice in front of the Reconstructions tab.

    A computer key arrives on the render thread and a MIDI key on the MIDI library's thread. Both strike the
    voice armed last, so a key sounds the same from either keyboard, and a MIDI key alone carries how hard it
    was struck. A press and its release reach the one owner of the keys played live, and ``follower`` draws
    where the note a press of the tab struck stands.

    A computer key names a note of the two octaves the piano rows span above the octave in force, as the
    tracker reads it, and a MIDI key names its own note.
    """

    def __init__(
        self,
        arming: KeyArming,
        live_keys: LiveKeysLogic,
        session_manager: SessionManager,
        *,
        follower: StrikeFollower,
    ) -> None:
        self._arming = arming
        self._live_keys = live_keys
        self._session_manager = session_manager
        self._follower = follower

    def press_computer_key(self, key_code: int, semitone: int) -> None:
        """Strikes the note a piano key names, ``semitone`` above the C of the octave in force.

        A computer key arrives on the render thread, so it arms the voice the tab shows at that moment,
        which a voice opened by the same frame's gestures is.
        """
        self._arming.arm()
        pitch = (self._session_manager.octave + OCTAVE_OFFSET) * OCTAVE_SEMITONES + semitone
        self._press(LiveKey(keyboard=Keyboard.COMPUTER, number=key_code), pitch, velocity=None)

    def lift_computer_key(self, key_code: int) -> None:
        self._live_keys.key_up(LiveKey(keyboard=Keyboard.COMPUTER, number=key_code))

    def press(self, note: int, velocity: int) -> None:
        """Strikes the note a MIDI key names, as hard as it was struck."""
        self._press(LiveKey(keyboard=Keyboard.MIDI, number=note), note, velocity=velocity)

    def lift(self, note: int) -> None:
        self._live_keys.key_up(LiveKey(keyboard=Keyboard.MIDI, number=note))

    def _press(self, key: LiveKey, pitch: int, *, velocity: Optional[int]) -> None:
        armed = self._arming.armed
        if armed is None:
            return

        self._live_keys.key_down(armed.strike(key, pitch, velocity=velocity, follower=self._follower))
