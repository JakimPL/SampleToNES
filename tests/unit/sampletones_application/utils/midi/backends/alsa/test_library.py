from typing import Final, List, Optional

import pytest

from sampletones_application.utils.midi.backends.alsa.library import (
    AlsaMidiConnection,
    SequencerBytes,
    SequencerCut,
    SequencerEvent,
    SequencerLeft,
)

alsa_midi = pytest.importorskip("alsa_midi", reason="alsa-midi is installed on Linux alone")

READER: Final = (128, 0)
SOURCE: Final = (24, 1)
NOTE: Final[bytes] = bytes((0x90, 60, 100))


class QueuedClient:
    """The binding's client as a connection reads it, handing out the events a case gave it."""

    def __init__(self, events: List[object]) -> None:
        self.client_id = READER[0]
        self._events = events

    def event_input(self, prefer_bytes: bool) -> object:
        assert prefer_bytes
        return self._events.pop(0)


class HeldPort:
    port_id = READER[1]


def _read(event: object) -> Optional[SequencerEvent]:
    return AlsaMidiConnection(QueuedClient([event]), HeldPort()).next_event()


class TestTranslation:
    """The binding's events reach the reader in its own terms: bytes, a client or port leaving, a cut."""

    def test_a_midi_message_arrives_as_its_bytes(self) -> None:
        assert _read(alsa_midi.MidiBytesEvent(NOTE)) == SequencerBytes(data=NOTE)

    def test_a_client_leaving_takes_every_port(self) -> None:
        assert _read(alsa_midi.ClientExitEvent(addr=SOURCE)) == SequencerLeft(client=SOURCE[0], port=None)

    def test_a_port_leaving_names_its_port(self) -> None:
        assert _read(alsa_midi.PortExitEvent(addr=SOURCE)) == SequencerLeft(client=SOURCE[0], port=SOURCE[1])

    def test_a_cut_names_both_ends(self) -> None:
        event = alsa_midi.PortUnsubscribedEvent(connect_sender=SOURCE, connect_dest=READER)

        assert _read(event) == SequencerCut(sender=SOURCE, destination=READER)

    @pytest.mark.parametrize(
        "event",
        [alsa_midi.ClientStartEvent(addr=SOURCE), alsa_midi.EchoEvent()],
        ids=["client-start", "echo"],
    )
    def test_an_event_the_reader_acts_on_nothing_for_reads_as_none(self, event: object) -> None:
        assert _read(event) is None

    def test_the_connection_stands_where_its_port_stands(self) -> None:
        assert AlsaMidiConnection(QueuedClient([]), HeldPort()).address == READER
