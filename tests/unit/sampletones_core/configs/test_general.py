from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config, GeneralConfig, PitchRange
from sampletones_core.constants.general import MAX_PITCH, MIN_PLAYED_PITCH
from sampletones_core.timers.utils import get_frequency_table

MIDDLE_PITCH: Final[int] = 60


class TestThePitchRangeIsOneInstructionsAccept:
    """The range a configuration states is held to the notes a tonal instruction names, so a
    library built from it holds instructions for every note it covers."""

    @pytest.mark.parametrize(
        "min_pitch, max_pitch",
        [(MIN_PLAYED_PITCH, MAX_PITCH), (MIN_PLAYED_PITCH, MIN_PLAYED_PITCH), (MAX_PITCH, MAX_PITCH)],
        ids=["the whole range", "the lowest note alone", "the highest note alone"],
    )
    def test_a_range_within_the_bounds_is_accepted(self, min_pitch: int, max_pitch: int) -> None:
        general = GeneralConfig(min_pitch=min_pitch, max_pitch=max_pitch)
        assert general.pitch_range == PitchRange(min_pitch=min_pitch, max_pitch=max_pitch)
        assert list(general.pitch_range.pitches) == list(range(min_pitch, max_pitch + 1))

    @pytest.mark.parametrize(
        "min_pitch, max_pitch",
        [
            (MIN_PLAYED_PITCH - 1, MAX_PITCH),
            (MIN_PLAYED_PITCH, MAX_PITCH + 1),
            (1, MAX_PITCH),
            (MIDDLE_PITCH + 1, MIDDLE_PITCH),
        ],
        ids=["below the lowest note", "above the highest note", "far below", "the lowest above the highest"],
    )
    def test_a_range_past_the_bounds_or_reversed_is_refused(self, min_pitch: int, max_pitch: int) -> None:
        with pytest.raises(ValidationError):
            GeneralConfig(min_pitch=min_pitch, max_pitch=max_pitch)

        with pytest.raises(ValidationError):
            PitchRange(min_pitch=min_pitch, max_pitch=max_pitch)

    def test_a_stored_configuration_with_a_reversed_range_is_refused_on_load(self) -> None:
        stored = Config().model_dump()
        stored["general"]["min_pitch"], stored["general"]["max_pitch"] = MAX_PITCH, MIN_PLAYED_PITCH

        with pytest.raises(ValidationError):
            Config.model_validate(stored)

    def test_the_frequency_table_covers_every_note_of_the_range(self) -> None:
        config = Config(general=GeneralConfig(min_pitch=MIDDLE_PITCH, max_pitch=MIDDLE_PITCH + 2))
        assert list(get_frequency_table(config)) == [MIDDLE_PITCH, MIDDLE_PITCH + 1, MIDDLE_PITCH + 2]
