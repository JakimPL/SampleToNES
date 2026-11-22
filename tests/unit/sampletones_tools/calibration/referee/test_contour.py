from typing import Final

import numpy as np
import pytest

from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.referee.contour import BAND_PREFIX, ONSET, SPREAD, ContourReferee

SAMPLE_RATE: Final[int] = 22050
SECONDS: Final[float] = 1.0
GAIN_6_DB: Final[float] = 10 ** (6 / 20)
TONE_FREQUENCY: Final[float] = 440.0
LEVEL_TOLERANCE_DECIBELS: Final[float] = 0.2
ATTACK_AMPLITUDE: Final[float] = 0.5
TAIL_AMPLITUDE: Final[float] = 0.0005
NO_OVERSHOOT_DECIBELS: Final[float] = 1.0


@pytest.fixture(name="config", scope="module")
def config_fixture() -> RefereeConfig:
    return RefereeConfig.load()


@pytest.fixture(name="referee", scope="module")
def referee_fixture(config: RefereeConfig) -> ContourReferee:
    return ContourReferee(SAMPLE_RATE, config=config)


@pytest.fixture(name="frame_length", scope="module")
def frame_length_fixture(config: RefereeConfig) -> int:
    return round(SAMPLE_RATE / config.contour_frame_rate)


def _tone(frequency: float, envelope: np.ndarray) -> np.ndarray:
    time = np.arange(len(envelope)) / SAMPLE_RATE
    return envelope * np.sin(2 * np.pi * frequency * time)


def _swell() -> np.ndarray:
    return np.linspace(0.05, 0.5, int(SECONDS * SAMPLE_RATE))


class TestContourReferee:
    def test_a_render_rising_and_falling_with_its_recording_scores_zero_at_any_offset(
        self, referee: ContourReferee
    ) -> None:
        recording = _tone(TONE_FREQUENCY, _swell())

        judgment = referee.judge(recording, 0.5 * recording)

        assert judgment.score == pytest.approx(0.0, abs=1e-6)
        assert judgment.components[SPREAD] == pytest.approx(0.0, abs=1e-6)

    def test_flattened_dynamics_read_as_a_narrower_spread(self, referee: ContourReferee) -> None:
        recording = _tone(TONE_FREQUENCY, _swell())
        flat = _tone(TONE_FREQUENCY, np.full_like(_swell(), 0.3))

        judgment = referee.judge(recording, flat)

        assert judgment.components[SPREAD] < -10.0
        assert judgment.score > 1.0

    def test_an_overshooting_attack_reads_above_zero(self, referee: ContourReferee) -> None:
        envelope = np.zeros(int(SECONDS * SAMPLE_RATE))
        envelope[SAMPLE_RATE // 2 :] = 0.2
        louder = envelope.copy()
        louder[SAMPLE_RATE // 2 : SAMPLE_RATE // 2 + SAMPLE_RATE // 30] = 0.6

        judgment = referee.judge(_tone(TONE_FREQUENCY, envelope), _tone(TONE_FREQUENCY, louder))

        assert judgment.components[ONSET] > 3.0

    def test_a_recording_sounding_from_its_first_frame_reads_an_onset_there(
        self, referee: ContourReferee, config: RefereeConfig, frame_length: int
    ) -> None:
        recording = _tone(TONE_FREQUENCY, np.full(int(SECONDS * SAMPLE_RATE), 0.2))
        louder_start = recording.copy()
        louder_start[: config.contour_onset_frames * frame_length] *= GAIN_6_DB

        judgment = referee.judge(recording, louder_start)

        assert judgment.components[ONSET] == pytest.approx(6.0, abs=LEVEL_TOLERANCE_DECIBELS)

    @pytest.mark.xfail(strict=True, reason="suspected bug: an onset reads the frames past a short attack")
    def test_an_onset_reads_the_frames_after_a_short_attack(self, referee: ContourReferee, frame_length: int) -> None:
        envelope = np.zeros(30 * frame_length)
        envelope[10 * frame_length : 11 * frame_length] = ATTACK_AMPLITUDE
        tail = np.zeros_like(envelope)
        tail[11 * frame_length : 13 * frame_length] = TAIL_AMPLITUDE
        recording = _tone(TONE_FREQUENCY, envelope)

        judgment = referee.judge(recording, recording + _tone(TONE_FREQUENCY, tail))

        assert judgment.components[ONSET] < NO_OVERSHOOT_DECIBELS

    def test_a_band_played_louder_reads_its_gain_in_decibels(self, referee: ContourReferee) -> None:
        steady = np.full(int(SECONDS * SAMPLE_RATE), 0.2)
        recording = _tone(125.0, steady) + _tone(1000.0, steady)
        brighter = _tone(125.0, steady) + GAIN_6_DB * _tone(1000.0, steady)

        judgment = referee.judge(recording, brighter)

        assert judgment.components[f"{BAND_PREFIX}1000"] == pytest.approx(6.0, abs=LEVEL_TOLERANCE_DECIBELS)
        assert judgment.components[f"{BAND_PREFIX}125"] == pytest.approx(0.0, abs=LEVEL_TOLERANCE_DECIBELS)
        assert f"{BAND_PREFIX}8000" not in judgment.components

    def test_a_band_the_render_leaves_silent_reads_far_below_zero(self, referee: ContourReferee) -> None:
        steady = np.full(int(SECONDS * SAMPLE_RATE), 0.2)
        recording = _tone(125.0, steady) + _tone(1000.0, steady)

        judgment = referee.judge(recording, _tone(125.0, steady))

        assert judgment.components[f"{BAND_PREFIX}1000"] < -60.0
