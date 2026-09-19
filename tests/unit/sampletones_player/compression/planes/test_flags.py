from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_player.compression.planes.flags import (
    flagged_ticks,
    flagged_value,
    is_flagged,
    note_flags,
    pitch_index,
)
from sampletones_player.specification.compression import PITCH_INDEX_MASK
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

INDEX: Final[int] = 33
NEIGHBOR: Final[int] = 34


class TestAValueByte:
    def test_a_flagged_value_names_its_index_and_its_flag(self) -> None:
        value = flagged_value(INDEX, True)
        assert (pitch_index(value), is_flagged(value)) == (INDEX, True)

    def test_an_unflagged_value_is_its_index(self) -> None:
        assert flagged_value(INDEX, False) == INDEX
        assert not is_flagged(INDEX)

    def test_an_index_reaching_the_flag_is_refused(self) -> None:
        with pytest.raises(ValueError):
            flagged_value(PITCH_INDEX_MASK + 1, False)

    def test_the_flagged_ticks_are_counted(self) -> None:
        value = bytes((flagged_value(INDEX, True), INDEX, flagged_value(INDEX, True)))
        assert flagged_ticks(value) == 2


class TestNoteFlags(BaseTestSuite):
    """A note is flagged from its first bent tick to its last, and a note that never bends is not."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        indices: Tuple[int, ...]
        offsets: Tuple[int, ...]
        expected: Tuple[bool, ...]

    test_cases = (
        TestCase(
            label="an unbent note carries no flag",
            indices=(INDEX,) * 3,
            offsets=(0, 0, 0),
            expected=(False, False, False),
        ),
        TestCase(
            label="a bend passing through zero keeps its note flagged",
            indices=(INDEX,) * 5,
            offsets=(0, 3, 0, -3, 0),
            expected=(False, True, True, True, False),
        ),
        TestCase(
            label="each note is flagged on its own",
            indices=(INDEX, INDEX, NEIGHBOR, NEIGHBOR),
            offsets=(0, 2, 0, 0),
            expected=(False, True, False, False),
        ),
        TestCase(
            label="a note returning after another is a note of its own",
            indices=(INDEX, NEIGHBOR, INDEX),
            offsets=(4, 0, 4),
            expected=(True, False, True),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_flags_match(self, test_case: TestCase) -> None:
        assert note_flags(test_case.indices, test_case.offsets) == test_case.expected

    def test_indices_and_offsets_covering_different_ticks_are_refused(self) -> None:
        with pytest.raises(ValueError):
            note_flags((INDEX,), ())
