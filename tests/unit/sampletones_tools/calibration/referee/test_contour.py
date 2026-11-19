from typing import Final

import numpy as np
import pytest

from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.referee.contour import ONSET, SPREAD, ContourReferee

SAMPLE_RATE: Final[int] = 22050
SECONDS: Final[float] = 1.0
GAIN_6_DB: Final[float] = 10 ** (6 / 20)


@pytest.fixture(name="referee", scope="module")
def referee_fixture() -> ContourReferee:
    return ContourReferee(SAMPLE_RATE, config=RefereeConfig.load())


def _tone(frequency: float, envelope: np.ndarray) -> np.ndarray:
    time = np.arange(len(envelope)) / SAMPLE_RATE
    return envelope * np.sin(2 * np.pi * frequency * time)


def _swell() -> np.ndarray:
    return np.linspace(0.05, 0.5, int(SECONDS * SAMPLE_RATE))


class TestContourReferee:
    def test_a_render_rising_and_falling_with_its_recording_scores_zero_at_any_offset(
        self, referee: ContourReferee
    ) -> None:
        recording = _tone(440.0, _swell())

        judgment = referee.judge(recording, 0.5 * recording)

        assert judgment.score == pytest.approx(0.0, abs=1e-6)
        assert judgment.components[SPREAD] == pytest.approx(0.0, abs=1e-6)

    def test_flattened_dynamics_read_as_a_narrower_spread(self, referee: ContourReferee) -> None:
        recording = _tone(440.0, _swell())
        flat = _tone(440.0, np.full_like(_swell(), 0.3))

        judgment = referee.judge(recording, flat)

        assert judgment.components[SPREAD] < -10.0
        assert judgment.score > 1.0

    def test_an_overshooting_attack_reads_above_zero(self, referee: ContourReferee) -> None:
        envelope = np.zeros(int(SECONDS * SAMPLE_RATE))
        envelope[SAMPLE_RATE // 2 :] = 0.2
        louder = envelope.copy()
        louder[SAMPLE_RATE // 2 : SAMPLE_RATE // 2 + SAMPLE_RATE // 30] = 0.6

        judgment = referee.judge(_tone(440.0, envelope), _tone(440.0, louder))

        assert judgment.components[ONSET] > 3.0

    def test_a_band_played_louder_reads_its_gain_in_decibels(self, referee: ContourReferee) -> None:
        steady = np.full(int(SECONDS * SAMPLE_RATE), 0.2)
        recording = _tone(125.0, steady) + _tone(1000.0, steady)
        brighter = _tone(125.0, steady) + GAIN_6_DB * _tone(1000.0, steady)

        judgment = referee.judge(recording, brighter)

        assert judgment.components["band-1000"] == pytest.approx(6.0, abs=0.2)
        assert judgment.components["band-125"] == pytest.approx(0.0, abs=0.2)
        assert "band-8000" not in judgment.components
