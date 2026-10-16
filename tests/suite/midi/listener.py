import threading
from typing import Final, List

from sampletones_application.utils.midi import MidiMessage

WAIT_SECONDS: Final[float] = 5.0


class RecordingListener:
    """A MIDI listener that keeps every message it hears and every port it loses."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self.messages: List[MidiMessage] = []
        self.losses: List[str] = []

    def heard(self, message: MidiMessage) -> None:
        with self._condition:
            self.messages.append(message)
            self._condition.notify_all()

    def lost(self, port_name: str) -> None:
        with self._condition:
            self.losses.append(port_name)
            self._condition.notify_all()

    def wait_for(self, message: MidiMessage) -> List[MidiMessage]:
        """The messages once ``message`` is among them, failing once ``WAIT_SECONDS`` pass first."""
        with self._condition:
            arrived = self._condition.wait_for(lambda: message in self.messages, timeout=WAIT_SECONDS)
            assert arrived, f"waited in vain for {message}, heard {self.messages}"
            return list(self.messages)

    def wait_for_loss(self) -> None:
        with self._condition:
            assert self._condition.wait_for(lambda: bool(self.losses), timeout=WAIT_SECONDS), "no port was lost"
