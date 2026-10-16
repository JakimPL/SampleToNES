from typing import List, Optional

import pytest

from sampletones_application.utils.midi.backends.portmidi.packing import wire_message


class TestUnpacking:
    """Each PortMidi event becomes the bytes its status names, and system exclusive pieces stay behind."""

    @pytest.mark.parametrize(
        ("packed", "message"),
        [
            ([0x90, 60, 100, 0], bytes((0x90, 60, 100))),
            ([0x85, 60, 64, 0], bytes((0x85, 60, 64))),
            ([0xB0, 64, 127, 0], bytes((0xB0, 64, 127))),
            ([0xE2, 0, 64, 0], bytes((0xE2, 0, 64))),
            ([0xC3, 5, 0, 0], bytes((0xC3, 5))),
            ([0xD0, 30, 0, 0], bytes((0xD0, 30))),
            ([0xF1, 0x23, 0, 0], bytes((0xF1, 0x23))),
            ([0xF2, 0x10, 0x01, 0], bytes((0xF2, 0x10, 0x01))),
            ([0xF8, 0, 0, 0], bytes((0xF8,))),
        ],
        ids=[
            "note-on",
            "note-off",
            "controller",
            "pitch-bend",
            "program",
            "pressure",
            "quarter-frame",
            "song",
            "clock",
        ],
    )
    def test_a_message_keeps_the_bytes_its_status_names(self, packed: List[int], message: Optional[bytes]) -> None:
        assert wire_message(packed) == message

    @pytest.mark.parametrize(
        "packed",
        [[0xF0, 0x7E, 0x7F, 0x09], [0x01, 0x02, 0x03, 0x04], [0x05, 0xF7, 0, 0], [0xF7, 0, 0, 0]],
        ids=["opening", "continuation", "closing-piece", "closing-byte"],
    )
    def test_system_exclusive_pieces_stay_behind(self, packed: List[int]) -> None:
        assert wire_message(packed) is None
