import threading
from typing import Optional

import numpy as np

from sampletones_application.logic.shared.synthesis import ChannelBank, EngineRates
from sampletones_core.audio.output import Fill
from sampletones_core.audio.output.source import FailureReport
from sampletones_core.configs import Config

from .held import HeldKeys
from .key import LiveKey
from .note import SoundingNote
from .strike import Strike


class LiveNoteSource:
    """The keys played live, sounded through the output as one playback while anything holds it.

    A press, a release and the pedal reach the source as its owner's commands, so each runs on the writer's
    thread between two reads, in the order played, and is heard from the next block. The held keys decide
    which press sounds, and the source sounds it: a press coming to the front strikes its note afresh, and a
    front left empty ends the note.

    The source sounds while a key is down or a note sounds, so a key returned to strikes on the stream
    already open. Once nothing holds it, it plays ``linger_seconds`` of silence before it ends, so keys
    played one after another share one stream, and a press during the linger is heard from the next block
    instead of after a stream opens.

    The generators are built at the first strike, for the stream's rate and the sound's settings, and built
    again for a strike under other settings. A strike under the same settings starts them from rest.
    """

    def __init__(self, *, sustained: bool, linger_seconds: float) -> None:
        """Starts with no key down.

        Args:
            sustained: Whether the sustain pedal is down as the playback starts.
            linger_seconds: The silence the source plays once nothing holds it, before it ends.
        """
        self._held = HeldKeys(sustained=sustained)
        self._linger_seconds = linger_seconds
        self._closed = threading.Event()
        self._output_rate: Optional[int] = None
        self._linger_frames: int = 0
        self._lingered: int = 0
        self._bank: Optional[ChannelBank] = None
        self._bank_config: Optional[Config] = None
        self._struck: Optional[Strike] = None
        self._sounding: Optional[SoundingNote] = None

    def press(self, strike: Strike) -> None:
        """Presses a key, whose sound is heard from the next block."""
        self._held.press(strike)
        self._follow_front()

    def release(self, key: LiveKey) -> None:
        """Lifts a key, which ends its note or returns to a key still held where it stands in front."""
        self._held.release(key)
        self._follow_front()

    def pedal(self, down: bool) -> None:
        """Takes the sustain pedal's state."""
        self._held.pedal(down)
        self._follow_front()

    def begin(self, output_rate: int, _failed: FailureReport) -> None:
        """Takes the stream's rate and strikes the key pressed before the stream opened.

        The notes are synthesized on the writer's thread alone, so a failure reaches the writer as its read
        raises.
        """
        self._output_rate = output_rate
        self._linger_frames = round(self._linger_seconds * output_rate)
        self._follow_front()

    def read_into(self, block: np.ndarray) -> Fill[None]:
        """Fills ``block`` with the note sounding and silence around it, short once the linger has run out."""
        if self._closed.is_set():
            return Fill(frames=0, reports=())

        sounded = self._sounded_into(block)
        block[sounded:] = 0.0
        if self._held.holds or self._sounding is not None:
            self._lingered = 0
            return Fill(frames=len(block), reports=())

        quiet = min(len(block) - sounded, self._linger_frames - self._lingered)
        self._lingered += quiet
        return Fill(frames=sounded + quiet, reports=())

    def close(self) -> None:
        """Ends the sound: every read from now on comes up empty."""
        self._closed.set()

    def _follow_front(self) -> None:
        """Sounds the press in front where it changed, once the stream's rate is known."""
        if self._output_rate is None:
            return

        front = self._held.front
        if front is self._struck:
            return

        self._struck = front
        if front is None:
            if self._sounding is not None:
                self._sounding.release()

            return

        self._sounding = SoundingNote(front.sound.note(), self._bank_for(front.sound.config, self._output_rate))

    def _sounded_into(self, block: np.ndarray) -> int:
        if self._sounding is None:
            return 0

        frames = self._sounding.fill(block)
        if self._sounding.finished:
            self._sounding = None

        return frames

    def _bank_for(self, config: Config, output_rate: int) -> ChannelBank:
        """The generators for ``config`` at the stream's rate, built where none are or other settings built them."""
        if self._bank is None or config != self._bank_config:
            self._bank = ChannelBank(config, EngineRates.from_config(config, output_rate))
            self._bank_config = config

        return self._bank
