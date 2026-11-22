from dataclasses import dataclass
from typing import List

import numpy as np
import pytest

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.corpus.stems import SINGLE_LINE_CAP, mixed, side_by_side, single_line
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestSingleLine(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channels: List[ChannelName]

    test_cases = (
        TestCase(channels=[ChannelName.TRIANGLE], label="a tonal channel"),
        TestCase(channels=[ChannelName.NOISE], label="the noise"),
        TestCase(channels=[ChannelName.PULSE1, ChannelName.PULSE2], label="either pulse"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_line_takes_its_channels_one_at_a_time_and_bends_the_tonal_ones(self, test_case: TestCase) -> None:
        settings = single_line(test_case.channels)

        assert settings.channels == tuple(test_case.channels)
        assert settings.bends == tuple(channel for channel in test_case.channels if channel in TONE_CHANNELS)
        assert dict(settings.drives) == {channel: UNIT_DRIVE for channel in test_case.channels}
        assert settings.channel_cap == SINGLE_LINE_CAP


class TestSideBySide:
    def test_every_stem_is_an_entry_in_order_on_one_level(self) -> None:
        stems = [single_line([ChannelName.TRIANGLE]), StemSettings.covering([ChannelName.PULSE1, ChannelName.NOISE])]

        setup = side_by_side(stems)

        assert [(entry.id, entry.settings) for entry in setup.entries] == list(enumerate(stems))
        assert setup.hierarchy.levels == ((0, 1),)

    def test_a_single_stem_stands_alone_on_its_level(self) -> None:
        setup = side_by_side([single_line([ChannelName.NOISE])])

        assert setup.hierarchy.levels == ((0,),)
        assert setup.covered_channels == frozenset({ChannelName.NOISE})


class TestMixed:
    def test_the_recordings_add_up_in_float32(self) -> None:
        first = np.array([0.25, -0.5, 0.0])
        second = np.array([0.25, 0.25, -0.125])

        mix = mixed((first, second))

        assert mix.dtype == np.float32
        np.testing.assert_array_equal(mix, np.array([0.5, -0.25, -0.125], dtype=np.float32))

    def test_one_recording_is_its_own_mix(self) -> None:
        recording = np.linspace(-1.0, 1.0, 9, dtype=np.float32)

        np.testing.assert_array_equal(mixed((recording,)), recording)
