from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.notes import NotesConfig

FIELDS: Final[Dict[str, Any]] = {
    "first_pitch": 33,
    "last_pitch": 45,
    "pitch_step": 6,
    "volumes": [15, 3],
    "duty_cycles": [2],
    "alternating_duty_cycles": [],
    "sounding_frames": 4,
    "silent_frames": 2,
    "listed_pitch_stride": 2,
    "listed_noise_period_stride": 4,
}


class TestNotesConfig:
    def test_the_grid_steps_from_its_first_pitch_up_to_its_last(self) -> None:
        assert NotesConfig.model_validate(FIELDS).pitches == [33, 39, 45]

    @pytest.mark.parametrize(
        "changed",
        [
            {"last_pitch": 32},
            {"volumes": [0]},
            {"volumes": [16]},
            {"duty_cycles": [4]},
            {"duty_cycles": [-1]},
            {"alternating_duty_cycles": [4]},
            {"duty_cycles": []},
        ],
        ids=[
            "last_below_first",
            "silent_volume",
            "volume_above_the_loudest",
            "unknown_duty",
            "negative_duty",
            "unknown_alternating_duty",
            "no_duty",
        ],
    )
    def test_a_grid_the_channels_cannot_play_is_refused(self, changed: Dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            NotesConfig.model_validate({**FIELDS, **changed})

    def test_a_grid_of_alternating_duty_cycles_alone_is_read(self) -> None:
        grid = NotesConfig.model_validate({**FIELDS, "duty_cycles": [], "alternating_duty_cycles": [1, 3]})

        assert grid.alternating_duty_cycles == [1, 3]

    def test_a_grid_of_one_pitch_holds_it_alone(self) -> None:
        assert NotesConfig.model_validate({**FIELDS, "last_pitch": FIELDS["first_pitch"]}).pitches == [33]

    def test_the_packaged_grid_reads(self) -> None:
        assert NotesConfig.load().pitches
