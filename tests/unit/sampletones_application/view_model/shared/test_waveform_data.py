from typing import Dict

import numpy as np
import pytest

from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.constants.enums import ChannelName


@pytest.fixture
def approximations() -> Dict[ChannelName, np.ndarray]:
    return {
        ChannelName.PULSE1: np.array([1.0, 0.0, -1.0, 0.0]),
        ChannelName.NOISE: np.array([0.5, 0.5, 0.5, 0.5]),
    }


@pytest.fixture
def waveform_data(approximations: Dict[ChannelName, np.ndarray]) -> WaveformData:
    return WaveformData(
        original_audio=np.zeros(4),
        approximation=np.array([1.5, 0.5, -0.5, 0.5]),
        approximations=approximations,
        coefficient=1.0,
        frame_length=2,
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
        waveform_data: WaveformData,
        approximations: Dict[ChannelName, np.ndarray],
    ) -> None:
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
        data = WaveformData(
            original_audio=approximation,
            approximation=approximation,
            approximations={ChannelName.PULSE1: np.array([0.5, 0.5]), ChannelName.NOISE: approximation},
            coefficient=1.0,
            frame_length=2,
        )

        result = data.partials([ChannelName.PULSE1, ChannelName.NOISE])

        expected = np.array([1.5, 0.5, -1.0, 0.0])
        assert np.array_equal(result, expected)

    def test_a_short_single_generator_reaches_the_approximation_length(self) -> None:
        approximation = np.array([1.0, 0.0, -1.0, 0.0])
        data = WaveformData(
            original_audio=approximation,
            approximation=approximation,
            approximations={ChannelName.PULSE1: np.array([0.5, 0.5])},
            coefficient=1.0,
            frame_length=2,
        )

        result = data.partials([ChannelName.PULSE1])

        expected = np.array([0.5, 0.5, 0.0, 0.0])
        assert np.array_equal(result, expected)
