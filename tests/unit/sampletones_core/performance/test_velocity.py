from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME, MIN_VOLUME
from sampletones_core.performance import velocity_level, velocity_levels
from sampletones_shared.constants.music import MAX_VELOCITY, MIN_VELOCITY

SCALING_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.NOISE]
VELOCITIES: Final[range] = range(MIN_VELOCITY, MAX_VELOCITY + 1)


class TestTheLevelAStrikePlaysAt:
    """The velocities share the levels evenly, from the softest strike at the quietest level to the hardest."""

    @pytest.mark.parametrize("channel_name", SCALING_CHANNELS, ids=[channel.value for channel in SCALING_CHANNELS])
    def test_the_softest_and_the_hardest_strike_reach_the_ends_of_the_levels(self, channel_name: ChannelName) -> None:
        assert velocity_level(channel_name, MIN_VELOCITY) == MIN_VOLUME
        assert velocity_level(channel_name, MAX_VELOCITY) == MAX_VOLUME

    def test_every_level_is_reached_and_a_harder_strike_is_never_quieter(self) -> None:
        levels = [velocity_level(ChannelName.PULSE1, velocity) for velocity in VELOCITIES]

        assert levels == sorted(levels, key=lambda level: level or 0)
        assert set(levels) == set(range(MIN_VOLUME, MAX_VOLUME + 1))

    def test_the_triangle_sounds_alike_however_hard_it_is_struck(self) -> None:
        assert {velocity_level(ChannelName.TRIANGLE, velocity) for velocity in VELOCITIES} == {None}
        assert velocity_level(ChannelName.PULSE1, MIN_VELOCITY) is not None

    @pytest.mark.parametrize("velocity", [MIN_VELOCITY - 1, MAX_VELOCITY + 1])
    def test_a_velocity_no_struck_key_reports_is_refused(self, velocity: int) -> None:
        with pytest.raises(ValueError):
            velocity_level(ChannelName.PULSE1, velocity)


class TestTheLevelsOfAStrike:
    """A strike names a level on every channel whose level it sets, and leaves the triangle out."""

    @pytest.mark.parametrize("velocity", [MIN_VELOCITY, MAX_VELOCITY])
    def test_every_channel_but_the_triangle_takes_the_level_its_velocity_names(self, velocity: int) -> None:
        levels = velocity_levels(velocity)

        assert set(levels) == set(ChannelName.items()) - {ChannelName.TRIANGLE}
        assert all(level == velocity_level(channel_name, velocity) for channel_name, level in levels.items())

    def test_a_velocity_no_struck_key_reports_is_refused(self) -> None:
        with pytest.raises(ValueError):
            velocity_levels(MAX_VELOCITY + 1)
