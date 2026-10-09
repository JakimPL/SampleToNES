from typing import Final

import numpy as np
import pytest

from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.referee.loudness import (
    ADDED_COMPONENT,
    LEVEL_COMPONENT,
    MISSING_COMPONENT,
    LoudnessWeightedReferee,
)

from .conftest import SAMPLE_RATE, ProbeSignals, decibels_to_gain

HARMONIC_DECIBELS: Final[float] = -20.0
LEVEL_OFFSET_DECIBELS: Final[float] = 3.0
NEARLY_FREE_SCORE: Final[float] = 1e-6


@pytest.fixture(scope="module", name="referee")
def referee_fixture(referee_config: RefereeConfig) -> LoudnessWeightedReferee:
    return LoudnessWeightedReferee(SAMPLE_RATE, config=referee_config)


class TestLoudnessWeightedReferee:
    def test_identical_signals_score_zero(self, referee: LoudnessWeightedReferee, probes: ProbeSignals) -> None:
        assert referee.judge(probes.sine, probes.sine).score == pytest.approx(0.0, abs=1e-9)

    def test_missing_and_added_sum_to_the_score(self, referee: LoudnessWeightedReferee, probes: ProbeSignals) -> None:
        judgment = referee.judge(probes.sine, probes.triangle())
        components = judgment.components
        assert components[MISSING_COMPONENT] + components[ADDED_COMPONENT] == pytest.approx(judgment.score)

    def test_silence_only_misses(self, referee: LoudnessWeightedReferee, probes: ProbeSignals) -> None:
        judgment = referee.judge(probes.sine, probes.silence)
        assert judgment.components[ADDED_COMPONENT] == pytest.approx(0.0, abs=1e-9)
        assert judgment.components[MISSING_COMPONENT] == pytest.approx(judgment.score)

    def test_an_added_harmonic_reads_as_added(self, referee: LoudnessWeightedReferee, probes: ProbeSignals) -> None:
        harmonic = probes.sine + probes.tone(440.0) * decibels_to_gain(HARMONIC_DECIBELS)
        components = referee.judge(probes.sine, harmonic).components
        assert components[MISSING_COMPONENT] < 0.1 * components[ADDED_COMPONENT]

    @pytest.mark.parametrize("offset", (LEVEL_OFFSET_DECIBELS, -LEVEL_OFFSET_DECIBELS), ids=("louder", "quieter"))
    def test_a_level_offset_reads_as_level_alone(
        self,
        referee: LoudnessWeightedReferee,
        probes: ProbeSignals,
        offset: float,
    ) -> None:
        judgment = referee.judge(probes.sine, probes.sine * decibels_to_gain(offset))
        assert judgment.components[LEVEL_COMPONENT] == pytest.approx(offset, abs=1e-6)
        assert judgment.score < NEARLY_FREE_SCORE

    def test_without_level_matching_a_level_offset_costs(
        self,
        referee_config: RefereeConfig,
        probes: ProbeSignals,
    ) -> None:
        unmatched = LoudnessWeightedReferee(
            SAMPLE_RATE, config=referee_config.model_copy(update={"level_matching": False})
        )
        judgment = unmatched.judge(probes.sine, probes.sine * decibels_to_gain(-LEVEL_OFFSET_DECIBELS))
        assert judgment.score == pytest.approx(LEVEL_OFFSET_DECIBELS, rel=0.05)

    def test_length_mismatch_raises_value_error(self, referee: LoudnessWeightedReferee, probes: ProbeSignals) -> None:
        with pytest.raises(ValueError):
            referee.judge(probes.sine, probes.sine[:-1])

    def test_a_silent_pair_scores_zero(self, referee: LoudnessWeightedReferee, probes: ProbeSignals) -> None:
        assert referee.judge(probes.silence, np.zeros_like(probes.silence)).score == pytest.approx(0.0, abs=1e-9)
