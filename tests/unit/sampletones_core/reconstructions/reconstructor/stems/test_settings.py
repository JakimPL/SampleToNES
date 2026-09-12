from dataclasses import dataclass
from typing import List, Optional, Type

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestTheBendsASettingsHolds(BaseTestSuite):
    """A bend names a channel the recording occupies and whose hardware loads a divider."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Optional[Type[Exception]]
        channels: List[ChannelName]
        bends: List[ChannelName]

    test_cases = (
        TestCase(
            label="bending_nothing",
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
            bends=[],
            expected=None,
        ),
        TestCase(
            label="bending_a_channel_it_occupies",
            channels=[ChannelName.PULSE1, ChannelName.TRIANGLE],
            bends=[ChannelName.TRIANGLE],
            expected=None,
        ),
        TestCase(
            label="bending_every_tone_channel_it_occupies",
            channels=list(sorted(TONE_CHANNELS)),
            bends=list(sorted(TONE_CHANNELS)),
            expected=None,
        ),
        TestCase(
            label="bending_a_channel_it_leaves_out",
            channels=[ChannelName.PULSE1],
            bends=[ChannelName.TRIANGLE],
            expected=ValidationError,
        ),
        TestCase(
            label="bending_the_noise_channel",
            channels=[ChannelName.NOISE],
            bends=[ChannelName.NOISE],
            expected=ValidationError,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_settings_are_held_to_their_bends(self, test_case: TestCase) -> None:
        if test_case.expected is None:
            settings = StemSettings(channels=test_case.channels, bends=test_case.bends)
            assert settings.bends == test_case.bends
            return

        with pytest.raises(test_case.expected):
            StemSettings(channels=test_case.channels, bends=test_case.bends)


class TestTheSetsSettingsAnswerWith:
    """The membership tests an assignment and the refinement each read once per frame."""

    def test_the_channel_set_holds_every_channel_occupied(self) -> None:
        settings = StemSettings(
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
            bends=[ChannelName.PULSE1],
        )
        assert settings.channel_set == frozenset({ChannelName.PULSE1, ChannelName.NOISE})

    def test_the_bend_set_holds_every_channel_bent(self) -> None:
        settings = StemSettings(
            channels=[ChannelName.PULSE1, ChannelName.TRIANGLE],
            bends=[ChannelName.TRIANGLE],
        )
        assert settings.bend_set == frozenset({ChannelName.TRIANGLE})
