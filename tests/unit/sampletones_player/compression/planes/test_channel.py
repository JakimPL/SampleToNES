import pytest
from pydantic import ValidationError

from sampletones_player.compression.planes.channel import ChannelPlanes


class TestAChannelWritesTwoPlanesOfEqualLength:
    """The two planes are read tick for tick, so a channel states both across the same ticks."""

    def test_both_planes_reach_the_ticks_the_channel_covers(self) -> None:
        planes = ChannelPlanes(control=bytes(4), value=bytes(4))
        assert planes.ticks == 4
        assert planes.ordered == (planes.control, planes.value)

    def test_planes_covering_different_ticks_are_refused(self) -> None:
        with pytest.raises(ValidationError):
            ChannelPlanes(control=bytes(3), value=bytes(2))

    def test_planes_covering_no_tick_are_refused(self) -> None:
        with pytest.raises(ValidationError):
            ChannelPlanes(control=b"", value=b"")
