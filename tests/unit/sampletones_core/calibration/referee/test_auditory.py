from typing import Final

import numpy as np
import pytest

from sampletones_core.calibration.config.referee import RefereeConfig
from sampletones_core.calibration.referee.auditory import MultiResolutionAuditoryReferee

SAMPLE_RATE: Final[int] = 22050
SIGNAL_SECONDS: Final[float] = 1.0


def _tone(frequency: float, amplitude: float = 0.5) -> np.ndarray:
    time = np.arange(int(SIGNAL_SECONDS * SAMPLE_RATE)) / SAMPLE_RATE
    return (amplitude * np.sin(2.0 * np.pi * frequency * time)).astype(np.float32)


@pytest.fixture(scope="module")
def referee() -> MultiResolutionAuditoryReferee:
    return MultiResolutionAuditoryReferee(SAMPLE_RATE, config=RefereeConfig.load())


class TestMultiResolutionAuditoryReferee:
    def test_identical_signals_score_zero(self, referee: MultiResolutionAuditoryReferee) -> None:
        tone = _tone(440.0)
        assert referee.score(tone, tone) == pytest.approx(0.0, abs=1e-9)

    def test_score_grows_with_the_distortion_level(self, referee: MultiResolutionAuditoryReferee) -> None:
        generator = np.random.default_rng(0)
        tone = _tone(440.0)
        noise = generator.standard_normal(tone.shape[0]).astype(np.float32)

        slightly_noisy = referee.score(tone, tone + 0.01 * noise)
        very_noisy = referee.score(tone, tone + 0.2 * noise)

        assert 0.0 < slightly_noisy < very_noisy

    def test_related_timbre_scores_closer_than_unrelated_noise(
        self,
        referee: MultiResolutionAuditoryReferee,
    ) -> None:
        """
        A candidate sharing the target's harmonic structure stays closer than
        broadband noise of the same level, which fills every auditory band.
        """
        target = _tone(220.0)
        time = np.arange(target.shape[0]) / SAMPLE_RATE
        square = (0.5 * np.sign(np.sin(2.0 * np.pi * 220.0 * time))).astype(np.float32)
        generator = np.random.default_rng(1)
        noise = (0.5 * generator.standard_normal(target.shape[0])).astype(np.float32)

        assert referee.score(target, square) < referee.score(target, noise)

    def test_score_is_invariant_under_a_common_gain(self, referee: MultiResolutionAuditoryReferee) -> None:
        """
        The audibility floor tracks the reference level, so scaling both signals
        together leaves the score unchanged.
        """
        generator = np.random.default_rng(2)
        tone = _tone(440.0)
        estimate = tone + (0.05 * generator.standard_normal(tone.shape[0])).astype(np.float32)

        base = referee.score(tone, estimate)
        scaled = referee.score(0.25 * tone, 0.25 * estimate)
        assert scaled == pytest.approx(base, rel=1e-6)

    def test_length_mismatch_raises_value_error(self, referee: MultiResolutionAuditoryReferee) -> None:
        tone = _tone(440.0)
        with pytest.raises(ValueError):
            referee.score(tone, tone[:-1])
