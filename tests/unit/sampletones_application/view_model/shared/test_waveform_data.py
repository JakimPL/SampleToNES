from typing import Dict, Final

import numpy as np
import pytest

from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.audio.mixing import mix
from sampletones_core.constants.enums import ChannelName

LARGE: Final[float] = 1e8
SMALL: Final[float] = 1.0


@pytest.fixture
def approximations() -> Dict[ChannelName, np.ndarray]:
    return {
        ChannelName.PULSE1: np.array([1.0, 0.0, -1.0, 0.0]),
        ChannelName.NOISE: np.array([0.5, 0.5, 0.5, 0.5]),
    }


@pytest.fixture
def waveform_data(approximations: Dict[ChannelName, np.ndarray]) -> WaveformData:
    return _waveform_data(approximations)


def _waveform_data(approximations: Dict[ChannelName, np.ndarray]) -> WaveformData:
    """Waveform data holding ``approximations`` and the mix of them, which is the shape the data holder builds."""
    return WaveformData(
        original_audio=np.zeros(4),
        approximation=mix(list(approximations.values())),
        approximations=approximations,
        coefficient=1.0,
        frame_length=2,
        sample_rate=44100,
    )


class TestPartials:
    def test_empty_selection_is_silent(self, waveform_data: WaveformData) -> None:
        assert np.all(waveform_data.partials([]) == 0.0)

    def test_missing_generator_is_silent(self, waveform_data: WaveformData) -> None:
        assert np.all(waveform_data.partials([ChannelName.TRIANGLE]) == 0.0)

    def test_single_generator_returns_its_approximation(
        self,
        waveform_data: WaveformData,
        approximations: Dict[ChannelName, np.ndarray],
    ) -> None:
        result = waveform_data.partials([ChannelName.PULSE1])

        assert np.array_equal(result, approximations[ChannelName.PULSE1])

    def test_selection_sums_the_selected_generators(
        self,
        approximations: Dict[ChannelName, np.ndarray],
    ) -> None:
        with_a_third = {**approximations, ChannelName.TRIANGLE: np.array([0.25, 0.25, 0.25, 0.25])}
        waveform_data = _waveform_data(with_a_third)

        result = waveform_data.partials([ChannelName.PULSE1, ChannelName.NOISE])

        expected = approximations[ChannelName.PULSE1] + approximations[ChannelName.NOISE]
        assert np.array_equal(result, expected)

    def test_unknown_generators_are_skipped_within_a_selection(
        self,
        waveform_data: WaveformData,
        approximations: Dict[ChannelName, np.ndarray],
    ) -> None:
        result = waveform_data.partials([ChannelName.PULSE1, ChannelName.TRIANGLE])

        assert np.array_equal(result, approximations[ChannelName.PULSE1])

    def test_short_generators_leave_the_tail_in_silence(self) -> None:
        approximation = np.array([1.0, 0.0, -1.0, 0.0])
        data = _waveform_data(
            {
                ChannelName.PULSE1: np.array([0.5, 0.5]),
                ChannelName.NOISE: approximation,
                ChannelName.TRIANGLE: np.zeros(4),
            }
        )

        result = data.partials([ChannelName.PULSE1, ChannelName.NOISE])

        expected = np.array([1.5, 0.5, -1.0, 0.0])
        assert np.array_equal(result, expected)

    def test_a_short_single_generator_reaches_the_approximation_length(self) -> None:
        data = _waveform_data({ChannelName.PULSE1: np.array([0.5, 0.5]), ChannelName.NOISE: np.zeros(4)})

        result = data.partials([ChannelName.PULSE1])

        expected = np.array([0.5, 0.5, 0.0, 0.0])
        assert np.array_equal(result, expected)


class TestEveryChannel:
    """A selection covering every channel answers the mix the data holds, in any listing."""

    def test_every_channel_answers_the_mix_itself(self, waveform_data: WaveformData) -> None:
        assert waveform_data.partials([ChannelName.PULSE1, ChannelName.NOISE]) is waveform_data.approximation

    def test_the_listing_order_makes_no_difference(self, waveform_data: WaveformData) -> None:
        assert waveform_data.partials([ChannelName.NOISE, ChannelName.PULSE1]) is waveform_data.approximation

    def test_channels_the_data_holds_none_of_change_nothing(self, waveform_data: WaveformData) -> None:
        every_channel = list(ChannelName.items())

        assert waveform_data.partials(every_channel) is waveform_data.approximation


class TestTheSumFollowsChannelOrder:
    """A narrower selection is summed in channel order, so the same choice reads the same samples.

    Adding the floats in another order rounds another way, which is what the readings would differ
    by if the sum followed the listing.
    """

    def test_two_listings_of_one_choice_read_the_same_samples(self) -> None:
        data = _waveform_data(
            {
                ChannelName.PULSE1: np.array([LARGE], dtype=np.float32),
                ChannelName.PULSE2: np.array([SMALL], dtype=np.float32),
                ChannelName.TRIANGLE: np.array([0.0], dtype=np.float32),
                ChannelName.NOISE: np.array([-LARGE], dtype=np.float32),
            }
        )
        choice = [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.NOISE]

        assert np.array_equal(data.partials(choice), data.partials(list(reversed(choice))))
