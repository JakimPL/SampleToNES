import pytest
from pydantic import ValidationError

from sampletones_shared.constants.music import (
    A4_FREQUENCY,
    A4_PITCH,
    LIMIT_MAX_PITCH,
    LIMIT_MIN_PITCH,
    MAX_A4_FREQUENCY,
    MIN_A4_FREQUENCY,
    OCTAVE_SEMITONES,
)
from sampletones_shared.music import Tuning


class TestDefaults:
    def test_the_default_is_standard_concert_pitch(self) -> None:
        tuning = Tuning()
        assert (tuning.a4_frequency, tuning.a4_pitch) == (A4_FREQUENCY, A4_PITCH)


class TestFrequency:
    def test_the_reference_pitch_sounds_the_reference_frequency(self) -> None:
        assert Tuning().frequency(A4_PITCH) == A4_FREQUENCY

    def test_an_octave_below_halves_the_frequency(self) -> None:
        assert Tuning().frequency(A4_PITCH - OCTAVE_SEMITONES) == A4_FREQUENCY / 2

    def test_a_retuned_reference_carries_the_whole_scale(self) -> None:
        tuning = Tuning(a4_frequency=432.0)
        assert tuning.frequency(A4_PITCH) == 432.0
        assert tuning.frequency(A4_PITCH - OCTAVE_SEMITONES) == 216.0

    def test_moving_the_reference_pitch_moves_every_frequency(self) -> None:
        tuning = Tuning(a4_pitch=A4_PITCH - OCTAVE_SEMITONES)
        assert tuning.frequency(A4_PITCH - OCTAVE_SEMITONES) == A4_FREQUENCY
        assert tuning.frequency(A4_PITCH) == A4_FREQUENCY * 2

    @pytest.mark.parametrize("pitch", [LIMIT_MIN_PITCH - 1, LIMIT_MAX_PITCH + 1])
    def test_a_pitch_beyond_the_projects_range_raises(self, pitch: int) -> None:
        with pytest.raises(ValueError):
            Tuning().frequency(pitch)


class TestValidation:
    @pytest.mark.parametrize("a4_frequency", [0.0, -440.0, MIN_A4_FREQUENCY, MAX_A4_FREQUENCY, 880.0])
    def test_a_reference_frequency_outside_the_tuning_band_raises(self, a4_frequency: float) -> None:
        with pytest.raises(ValidationError):
            Tuning(a4_frequency=a4_frequency)

    @pytest.mark.parametrize("a4_pitch", [LIMIT_MIN_PITCH - 1, LIMIT_MAX_PITCH + 1])
    def test_a_reference_pitch_beyond_the_projects_range_raises(self, a4_pitch: int) -> None:
        with pytest.raises(ValidationError):
            Tuning(a4_pitch=a4_pitch)

    def test_the_tuning_holds_still(self) -> None:
        with pytest.raises(ValidationError):
            Tuning().a4_frequency = 432.0
