from typing import Final

import pytest

from sampletones_application.view_model.shared.midi_settings import key_name
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH

NUMBER_TEMPLATE: Final[str] = "key {number}"
MIDDLE_C: Final[int] = 60


class TestKeyName:
    """A key is named as the tracker names its note, and by its number below the notes the tracker names."""

    def test_middle_c_is_named_as_the_tracker_writes_it(self) -> None:
        assert key_name(MIDDLE_C, number_template=NUMBER_TEMPLATE) == "C-3"

    @pytest.mark.parametrize("note", [LIMIT_MIN_PITCH, LIMIT_MAX_PITCH])
    def test_the_outermost_named_notes_keep_their_names(self, note: int) -> None:
        assert key_name(note, number_template=NUMBER_TEMPLATE) != NUMBER_TEMPLATE.format(number=note)

    @pytest.mark.parametrize("note", [0, LIMIT_MIN_PITCH - 1])
    def test_a_key_below_the_named_notes_is_named_by_its_number(self, note: int) -> None:
        assert key_name(note, number_template=NUMBER_TEMPLATE) == NUMBER_TEMPLATE.format(number=note)
