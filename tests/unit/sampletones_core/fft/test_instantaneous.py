import math
from typing import Final, List, Optional

import numpy as np
import pytest

from sampletones_core.fft.instantaneous import FundamentalReading, InstantaneousPitch

SAMPLE_RATE: Final[int] = 44100
HOP: Final[int] = 735
SECONDS: Final[float] = 0.5
A4_FREQUENCY: Final[float] = 440.0
CENTS_PER_OCTAVE: Final[float] = 1200.0
CENT_TOLERANCE: Final[float] = 1.0
PITCHED_CONFIDENCE: Final[float] = 0.2
UNPITCHED_CONFIDENCE: Final[float] = 0.1
NOISE_SEED: Final[int] = 4


def _harmonic(frequency: float, seed: int = 0) -> np.ndarray:
    """A steady tone with a full harmonic series, which is what a pitched frame looks like."""
    generator = np.random.default_rng(seed)
    count = int(SAMPLE_RATE * SECONDS)
    time = np.arange(count) / SAMPLE_RATE
    audio = np.zeros(count)
    for harmonic in range(1, 20):
        if frequency * harmonic > SAMPLE_RATE / 2:
            break

        audio += np.sin(2 * np.pi * frequency * harmonic * time + generator.uniform(0, 2 * np.pi)) / harmonic

    return (audio / np.abs(audio).max() * 0.3).astype(np.float32)


def _readings(audio: np.ndarray, reference: float) -> List[FundamentalReading]:
    reader = InstantaneousPitch(audio, SAMPLE_RATE, HOP)
    read: List[Optional[FundamentalReading]] = [reader.at(frame, reference) for frame in range(reader.columns)]
    return [reading for reading in read if reading is not None]


def _median_cents(readings: List[FundamentalReading], reference: float) -> float:
    return CENTS_PER_OCTAVE * math.log2(float(np.median([reading.frequency for reading in readings])) / reference)


class TestReadingAFundamental:
    @pytest.mark.parametrize("cents", (-45.0, -18.0, 0.0, 25.0, 40.0), ids=lambda cents: f"{cents:+.0f}c")
    def test_a_tone_between_two_notes_is_read_where_it_stands(self, cents: float) -> None:
        """The bins are a semitone apart, and the phase places the tone far inside one of them."""
        truth = A4_FREQUENCY * 2 ** (cents / CENTS_PER_OCTAVE)

        readings = _readings(_harmonic(truth), A4_FREQUENCY)

        assert readings
        assert abs(_median_cents(readings, A4_FREQUENCY) - cents) < CENT_TOLERANCE

    def test_a_reading_is_taken_for_every_frame_of_the_recording(self) -> None:
        reader = InstantaneousPitch(_harmonic(A4_FREQUENCY), SAMPLE_RATE, HOP)

        assert all(reader.at(frame, A4_FREQUENCY) is not None for frame in range(reader.columns))

    def test_a_frame_outside_the_recording_is_read_as_nothing(self) -> None:
        reader = InstantaneousPitch(_harmonic(A4_FREQUENCY), SAMPLE_RATE, HOP)

        assert reader.at(-1, A4_FREQUENCY) is None
        assert reader.at(reader.columns, A4_FREQUENCY) is None

    def test_a_reference_the_transform_never_reaches_is_read_as_nothing(self) -> None:
        reader = InstantaneousPitch(_harmonic(A4_FREQUENCY), SAMPLE_RATE, HOP)

        assert reader.at(1, SAMPLE_RATE) is None


class TestHowMuchOfAFrameStandsBehindItsReading:
    def test_a_pitched_frame_reads_with_confidence(self) -> None:
        readings = _readings(_harmonic(A4_FREQUENCY), A4_FREQUENCY)

        assert float(np.median([reading.confidence for reading in readings])) > PITCHED_CONFIDENCE

    def test_noise_reads_with_none(self) -> None:
        """Noise spreads its energy everywhere, so the harmonics of any note hold little of it."""
        count = int(SAMPLE_RATE * SECONDS)
        noise = np.random.default_rng(NOISE_SEED).normal(0.0, 0.3, count).astype(np.float32)

        readings = _readings(noise, A4_FREQUENCY)

        assert float(np.median([reading.confidence for reading in readings])) < UNPITCHED_CONFIDENCE

    def test_a_tone_sharing_the_frame_lowers_the_share_without_moving_the_reading(self) -> None:
        alone = _harmonic(A4_FREQUENCY)
        crowded = alone + _harmonic(A4_FREQUENCY * 1.5, seed=7)

        readings = _readings(crowded, A4_FREQUENCY)

        assert abs(_median_cents(readings, A4_FREQUENCY)) < CENT_TOLERANCE
        assert float(np.median([reading.confidence for reading in readings])) < float(
            np.median([reading.confidence for reading in _readings(alone, A4_FREQUENCY)])
        )
