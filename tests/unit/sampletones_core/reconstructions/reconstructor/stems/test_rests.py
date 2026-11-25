from typing import Dict, Final, List

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import RESTING_FRAME_COST, STEM_ACTIVITY_FLOOR
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.assignment.rests import (
    resting,
    silent_contribution,
    sounding_stems,
)
from sampletones_core.structures.histogram import Histogram
from tests.suite.base import BaseTestSuite

BINS: Final[int] = 3
QUIETER: Final[float] = 0.5
LOUDER: Final[float] = 2.0
RESTED: Final[List[ChannelName]] = [ChannelName.NOISE, ChannelName.PULSE1]


def _fragment(config: Config, peak: float) -> Fragment:
    """A frame whose waveform peaks at ``peak``, reached once below zero, held in double precision to keep it exact."""
    audio = np.zeros(config.frame_length, dtype=np.float64)
    audio[1] = -peak
    return Fragment(
        audio=audio,
        feature=Histogram(edges=np.arange(BINS + 1, dtype=np.float32), values=np.zeros(BINS, dtype=np.float32)),
        config=config,
    )


class TestSoundingStems(BaseTestSuite):
    """A stem stands aside in a frame quieter than the quietest note the hardware plays."""

    def test_a_frame_reaching_the_floor_sounds_and_one_under_it_stands_aside(self, config: Config) -> None:
        fragments = {
            0: _fragment(config, STEM_ACTIVITY_FLOOR),
            1: _fragment(config, STEM_ACTIVITY_FLOOR * QUIETER),
            2: _fragment(config, STEM_ACTIVITY_FLOOR * LOUDER),
            3: _fragment(config, 0.0),
        }

        assert sounding_stems(fragments) == frozenset({0, 2})

    def test_no_stem_sounds_no_frame(self) -> None:
        assert sounding_stems({}) == frozenset()


class TestResting(BaseTestSuite):
    @pytest.fixture(name="fragment")
    def fragment_fixture(self, config: Config) -> Fragment:
        return _fragment(config, STEM_ACTIVITY_FLOOR)

    def test_each_resting_channel_holds_its_silence_alone_at_the_resting_cost_in_the_order_named(
        self, fragment: Fragment, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        rests = resting(RESTED, all_channels, fragment)

        assert [rest.channel_name for rest in rests] == RESTED
        for rest in rests:
            (candidate,) = rest.column
            assert candidate.instruction == all_channels[rest.channel_name].get_instruction_type().null_instruction()
            assert candidate.cost == RESTING_FRAME_COST
            assert not candidate.contribution.sounding

    def test_a_silent_channel_adds_no_power_and_no_waveform_to_the_frame(self, fragment: Fragment) -> None:
        silence = silent_contribution(fragment)

        assert np.array_equal(silence.power, np.zeros(BINS))
        assert np.array_equal(silence.expectation, np.zeros(fragment.audio.shape[0]))
        assert silence.variance == 0.0
        assert not silence.sounding

    def test_no_channel_named_rests_none(
        self, fragment: Fragment, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        assert resting([], all_channels, fragment) == ()
