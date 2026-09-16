from typing import Final

from sampletones_application.view_model.main.source import (
    CHANNEL_CAP_STEPS,
    ChannelSettingsViewModel,
)
from sampletones_application.view_model.shared.agreement import Agreement
from sampletones_core.constants.algorithm import ALL_STEMS_CHANNEL_CAP, MIN_STEMS_CHANNEL_CAP
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite

LOUD_DRIVE: Final[float] = 2.0


def _channel(
    channel_name: ChannelName,
    use: Agreement,
    bend: Agreement = Agreement.NONE,
) -> ChannelSettingsViewModel:
    return ChannelSettingsViewModel(channel=channel_name, use=use, bend=bend, drive=LOUD_DRIVE)


class TestWhenABendIsOffered(BaseTestSuite):
    """A bend belongs to a channel a recording occupies whose hardware loads a divider."""

    def test_a_tone_channel_a_recording_occupies_offers_one(self) -> None:
        assert _channel(ChannelName.TRIANGLE, Agreement.ALL).bend_offered is True

    def test_a_tone_channel_some_of_them_occupy_still_offers_one(self) -> None:
        assert _channel(ChannelName.PULSE1, Agreement.SOME).bend_offered is True

    def test_a_channel_none_of_them_occupy_offers_none(self) -> None:
        assert _channel(ChannelName.PULSE1, Agreement.NONE).bend_offered is False

    def test_the_noise_channel_offers_none(self) -> None:
        noise = _channel(ChannelName.NOISE, Agreement.ALL)

        assert (noise.bendable, noise.bend_offered) == (False, False)


class TestTheStepsTheCountOffers(BaseTestSuite):
    def test_the_steps_run_from_one_channel_to_them_all(self) -> None:
        assert CHANNEL_CAP_STEPS == tuple(range(MIN_STEMS_CHANNEL_CAP, ALL_STEMS_CHANNEL_CAP + 1))
