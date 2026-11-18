from dataclasses import dataclass
from typing import Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import (
    ATTRIBUTE_TABLE_SIZE,
    NAMETABLE_SIZE,
    PALETTE_SIZE,
    SPRITE_MEMORY_SIZE,
)
from sampletones_tools.player.graphics.picture.picture import Picture
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SIZES: Final[Dict[str, int]] = {
    "nametable": NAMETABLE_SIZE,
    "attributes": ATTRIBUTE_TABLE_SIZE,
    "palette": PALETTE_SIZE,
    "sprites": SPRITE_MEMORY_SIZE,
}
BLANK: Final[Dict[str, bytes]] = {part: bytes(size) for part, size in SIZES.items()}


class TestAPicture(BaseTestSuite):
    def test_parts_of_their_sizes_are_held_as_stated(self) -> None:
        assert Picture.model_validate(BLANK).model_dump() == BLANK


class TestAPictureTheModelRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        part: str
        excess: int

    test_cases = (
        TestCase(part="nametable", excess=-1, label="a nametable a byte short"),
        TestCase(part="attributes", excess=1, label="attributes a byte over"),
        TestCase(part="palette", excess=-1, label="a palette a byte short"),
        TestCase(part="sprites", excess=1, label="a sprite memory a byte over"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_the_part(self, test_case: TestCase) -> None:
        stated = {**BLANK, test_case.part: bytes(SIZES[test_case.part] + test_case.excess)}

        with pytest.raises(ValidationError, match=f"picture's {test_case.part}"):
            Picture.model_validate(stated)
