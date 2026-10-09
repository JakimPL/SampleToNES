from typing import Final

import numpy as np
import pytest

from sampletones_tools.calibration.referee.level import (
    k_weighted_energy,
    level_difference_decibels,
    matched_to_reference,
)

from .conftest import SAMPLE_RATE, ProbeSignals, decibels_to_gain

ENERGY_FLOOR: Final[float] = 1e-10
RANGE_DECIBELS: Final[float] = 60.0
LEVEL_OFFSET_DECIBELS: Final[float] = 3.0


class TestKWeightedEnergy:
    def test_energy_grows_with_the_square_of_a_gain(self, probes: ProbeSignals) -> None:
        assert k_weighted_energy(2.0 * probes.sine, SAMPLE_RATE) == pytest.approx(
            4.0 * k_weighted_energy(probes.sine, SAMPLE_RATE)
        )

    def test_a_low_tone_weighs_less_than_a_mid_tone_of_the_same_amplitude(self, probes: ProbeSignals) -> None:
        assert k_weighted_energy(probes.tone(40.0), SAMPLE_RATE) < k_weighted_energy(probes.tone(1000.0), SAMPLE_RATE)


class TestLevelDifference:
    @pytest.mark.parametrize("offset", (LEVEL_OFFSET_DECIBELS, -LEVEL_OFFSET_DECIBELS), ids=("louder", "quieter"))
    def test_a_scaled_copy_reads_its_gain_in_decibels(self, probes: ProbeSignals, offset: float) -> None:
        level = level_difference_decibels(
            probes.sine,
            probes.sine * decibels_to_gain(offset),
            SAMPLE_RATE,
            energy_floor=ENERGY_FLOOR,
            range_decibels=RANGE_DECIBELS,
        )
        assert level == pytest.approx(offset, abs=1e-6)

    def test_silence_reads_the_whole_range_quieter(self, probes: ProbeSignals) -> None:
        level = level_difference_decibels(
            probes.sine,
            probes.silence,
            SAMPLE_RATE,
            energy_floor=ENERGY_FLOOR,
            range_decibels=RANGE_DECIBELS,
        )
        assert level == -RANGE_DECIBELS

    def test_matching_brings_a_scaled_copy_back_to_the_reference(self, probes: ProbeSignals) -> None:
        louder = probes.sine * decibels_to_gain(LEVEL_OFFSET_DECIBELS)
        matched = matched_to_reference(louder, level_decibels=LEVEL_OFFSET_DECIBELS)
        assert np.allclose(matched, probes.sine)
