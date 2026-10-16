from typing import Final

import pytest

from sampletones_application.logic.shared.synthesis import ChannelBank, EngineRates
from sampletones_core.configs import Config
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.enums import ChannelName

NES_FREQUENCY: Final[int] = 60
HALF_FREQUENCY: Final[int] = 30
OTHER_SAMPLE_RATE: Final[int] = 48000
RATES: Final[EngineRates] = EngineRates(nes_frequency=NES_FREQUENCY, sample_rate=DEFAULT_SAMPLE_RATE)


@pytest.fixture
def bank() -> ChannelBank:
    return ChannelBank(Config(), RATES)


class TestFollowingTheRates:
    """The generators and the tick clock follow the rates together, and stay as they are while the rates do."""

    def test_the_same_rates_keep_every_generator(self, bank: ChannelBank) -> None:
        generators = {channel_name: bank.generator(channel_name) for channel_name in ChannelName.items()}

        bank.follow(RATES)

        assert all(bank.generator(channel_name) is generator for channel_name, generator in generators.items())

    @pytest.mark.parametrize(
        "rates",
        [
            EngineRates(nes_frequency=HALF_FREQUENCY, sample_rate=DEFAULT_SAMPLE_RATE),
            EngineRates(nes_frequency=NES_FREQUENCY, sample_rate=OTHER_SAMPLE_RATE),
        ],
        ids=["engine-rate", "sample-rate"],
    )
    def test_a_new_rate_rebuilds_the_generators_and_the_clock(self, bank: ChannelBank, rates: EngineRates) -> None:
        before = bank.generator(ChannelName.PULSE1)

        bank.follow(rates)

        assert bank.generator(ChannelName.PULSE1) is not before
        assert bank.clock == rates.clock()
