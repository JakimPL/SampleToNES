import logging
from typing import Dict, Tuple

import pytest

from sampletones_core.famitracker.sequences.lengths import equalize_lengths
from sampletones_core.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
    SequenceKind,
)


def items_of(length: int) -> Tuple[int, ...]:
    return tuple(index % 16 for index in range(length))


def volume_and_arpeggio(length: int) -> Dict[SequenceKind, Tuple[int, ...]]:
    return {
        SequenceKind.VOLUME: items_of(length),
        SequenceKind.ARPEGGIO: (0,) * length,
        SequenceKind.PITCH: (),
        SequenceKind.HI_PITCH: (),
        SequenceKind.DUTY: (),
    }


class TestEqualizeLengths:
    def test_loop_takes_the_shortest_populated_dimension(self) -> None:
        equalized = equalize_lengths(
            {SequenceKind.VOLUME: (15, 12, 9, 0), SequenceKind.ARPEGGIO: (0, 2, 4)},
            loop=True,
        )
        assert equalized[SequenceKind.VOLUME] == (15, 12, 9)
        assert equalized[SequenceKind.ARPEGGIO] == (0, 2, 4)

    def test_one_shot_holds_the_shorter_dimensions_final_value(self) -> None:
        equalized = equalize_lengths(
            {SequenceKind.VOLUME: (15, 12, 9, 0), SequenceKind.ARPEGGIO: (0, 2, 4)},
            loop=False,
        )
        assert equalized[SequenceKind.VOLUME] == (15, 12, 9, 0)
        assert equalized[SequenceKind.ARPEGGIO] == (0, 2, 4, 4)

    def test_empty_dimensions_stay_empty(self) -> None:
        equalized = equalize_lengths(
            {SequenceKind.VOLUME: (15, 12, 0), SequenceKind.ARPEGGIO: ()},
            loop=False,
        )
        assert equalized[SequenceKind.ARPEGGIO] == ()

    def test_all_dimensions_empty_stay_empty(self) -> None:
        equalized = equalize_lengths({kind: () for kind in SequenceKind}, loop=True)
        assert all(items == () for items in equalized.values())


class TestFamiTrackerItemLimit:
    @pytest.mark.parametrize("loop", [False, True], ids=["one_shot", "loop"])
    def test_an_over_long_envelope_keeps_its_opening_items(self, loop: bool) -> None:
        length = MAX_SEQUENCE_ITEMS + 48

        equalized = equalize_lengths(volume_and_arpeggio(length), loop=loop)

        assert equalized[SequenceKind.VOLUME] == items_of(MAX_SEQUENCE_ITEMS)
        assert len(equalized[SequenceKind.ARPEGGIO]) == MAX_SEQUENCE_ITEMS

    def test_an_over_long_envelope_is_reported(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            equalize_lengths(volume_and_arpeggio(MAX_SEQUENCE_ITEMS + 1), loop=False)

        assert str(MAX_SEQUENCE_ITEMS) in caplog.text

    def test_an_envelope_within_the_limit_is_quiet(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            equalize_lengths(volume_and_arpeggio(MAX_SEQUENCE_ITEMS), loop=False)

        assert caplog.text == ""
