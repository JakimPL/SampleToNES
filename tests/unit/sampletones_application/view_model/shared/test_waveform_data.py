from typing import Dict

import numpy as np
import pytest

from sampletones_application.view_model.shared.waveform_data import WaveformData
from sampletones_core.constants.enums import GeneratorName


@pytest.fixture
def approximations() -> Dict[GeneratorName, np.ndarray]:
    return {
        GeneratorName.PULSE1: np.array([1.0, 0.0, -1.0, 0.0]),
        GeneratorName.NOISE: np.array([0.5, 0.5, 0.5, 0.5]),
    }


@pytest.fixture
def waveform_data(approximations: Dict[GeneratorName, np.ndarray]) -> WaveformData:
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
        assert np.all(waveform_data.partials([GeneratorName.TRIANGLE]) == 0.0)

    def test_single_generator_returns_its_approximation(
        self,
        waveform_data: WaveformData,
        approximations: Dict[GeneratorName, np.ndarray],
    ) -> None:
        result = waveform_data.partials([GeneratorName.PULSE1])

        assert np.array_equal(result, approximations[GeneratorName.PULSE1])

    def test_selection_sums_the_selected_generators(
        self,
        waveform_data: WaveformData,
        approximations: Dict[GeneratorName, np.ndarray],
    ) -> None:
        result = waveform_data.partials([GeneratorName.PULSE1, GeneratorName.NOISE])

        expected = approximations[GeneratorName.PULSE1] + approximations[GeneratorName.NOISE]
        assert np.array_equal(result, expected)

    def test_unknown_generators_are_skipped_within_a_selection(
        self,
        waveform_data: WaveformData,
        approximations: Dict[GeneratorName, np.ndarray],
    ) -> None:
        result = waveform_data.partials([GeneratorName.PULSE1, GeneratorName.TRIANGLE])

        assert np.array_equal(result, approximations[GeneratorName.PULSE1])
