from typing import Final

import pytest

from tests.suite.audio.machine import SPEAKERS, ticking_machine
from tests.suite.audio.ramp import ramp
from tests.suite.audio.timeline import Closed

BLOCK: Final[int] = 64


class TestTickerPacing:
    """A ticking device plays what it is given at a faster pace and drains what it still holds."""

    def test_a_drained_stream_holds_nothing_to_discard(self) -> None:
        system = ticking_machine([SPEAKERS], default_device=0)
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        for index in range(4):
            stream.write(ramp(BLOCK, start=index * BLOCK).tobytes())

        stream.drain()
        stream.close()

        [closed] = system.timeline.of(Closed)
        assert closed.discarded == 0

    @pytest.mark.parametrize("blocks", [1, 8], ids=["one_block", "several_blocks"])
    def test_every_write_reaches_the_timeline_in_order(self, blocks: int) -> None:
        system = ticking_machine([SPEAKERS], default_device=0)
        stream = system.driver().open_output(device_index=0, sample_rate=44100, frames_per_buffer=BLOCK)
        for index in range(blocks):
            stream.write(ramp(BLOCK, start=index * BLOCK).tobytes())

        stream.drain()

        assert len(system.timeline.written()) == blocks * BLOCK
