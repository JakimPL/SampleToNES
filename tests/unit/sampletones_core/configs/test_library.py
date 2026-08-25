from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.configs.library import InstructionsLibraryConfig
from sampletones_shared.constants.music import (
    LIMIT_MAX_PITCH,
    LIMIT_MIN_PITCH,
    MAX_A4_FREQUENCY,
    MIN_A4_FREQUENCY,
)
from sampletones_shared.music import Tuning

RETUNED_A4_FREQUENCY: Final[float] = 432.0


class TestTuning:
    def test_the_tuning_states_the_configured_reference(self) -> None:
        library = InstructionsLibraryConfig(a4_frequency=RETUNED_A4_FREQUENCY, a4_pitch=57)
        assert library.tuning == Tuning(a4_frequency=RETUNED_A4_FREQUENCY, a4_pitch=57)

    def test_the_configuration_reads_its_librarys_tuning(self) -> None:
        config = Config(library=InstructionsLibraryConfig(a4_frequency=RETUNED_A4_FREQUENCY))
        assert config.tuning == config.library.tuning
        assert config.tuning.a4_frequency == RETUNED_A4_FREQUENCY


class TestReference:
    @pytest.mark.parametrize("a4_frequency", [MIN_A4_FREQUENCY, MAX_A4_FREQUENCY])
    def test_a_reference_frequency_outside_the_tuning_band_raises(self, a4_frequency: float) -> None:
        with pytest.raises(ValidationError):
            InstructionsLibraryConfig(a4_frequency=a4_frequency)

    @pytest.mark.parametrize("a4_pitch", [LIMIT_MIN_PITCH - 1, LIMIT_MAX_PITCH + 1])
    def test_a_reference_pitch_beyond_the_projects_range_raises(self, a4_pitch: int) -> None:
        with pytest.raises(ValidationError):
            InstructionsLibraryConfig(a4_pitch=a4_pitch)
