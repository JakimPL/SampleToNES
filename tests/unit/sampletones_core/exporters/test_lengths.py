import logging
from typing import Dict, Final, Tuple

import pytest

from sampletones_core.exporters.lengths import equalize_lengths, limit_lengths

VOLUME: Final[str] = "volume"
ARPEGGIO: Final[str] = "arpeggio"
DUTY: Final[str] = "duty"

ITEM_LIMIT: Final[int] = 252


def items_of(length: int) -> Tuple[int, ...]:
    return tuple(index % 16 for index in range(length))


def volume_and_arpeggio(length: int) -> Dict[str, Tuple[int, ...]]:
    return {
        VOLUME: items_of(length),
        ARPEGGIO: (0,) * length,
        DUTY: (),
    }


class TestEqualizeLengths:
    def test_loop_takes_the_shortest_populated_dimension(self) -> None:
        equalized = equalize_lengths({VOLUME: (15, 12, 9, 0), ARPEGGIO: (0, 2, 4)}, loop=True)
        assert equalized[VOLUME] == (15, 12, 9)
        assert equalized[ARPEGGIO] == (0, 2, 4)

    def test_one_shot_holds_the_shorter_dimensions_final_value(self) -> None:
        equalized = equalize_lengths({VOLUME: (15, 12, 9, 0), ARPEGGIO: (0, 2, 4)}, loop=False)
        assert equalized[VOLUME] == (15, 12, 9, 0)
        assert equalized[ARPEGGIO] == (0, 2, 4, 4)

    def test_empty_dimensions_stay_empty(self) -> None:
        equalized = equalize_lengths({VOLUME: (15, 12, 0), ARPEGGIO: ()}, loop=False)
        assert equalized[ARPEGGIO] == ()

    def test_all_dimensions_empty_stay_empty(self) -> None:
        equalized = equalize_lengths({VOLUME: (), ARPEGGIO: (), DUTY: ()}, loop=True)
        assert all(items == () for items in equalized.values())


class TestLimitLengths:
    def test_every_dimension_keeps_its_own_length(self) -> None:
        limited = limit_lengths({VOLUME: (15, 12, 9, 0), ARPEGGIO: (0, 2, 4)}, limit=ITEM_LIMIT)
        assert limited[VOLUME] == (15, 12, 9, 0)
        assert limited[ARPEGGIO] == (0, 2, 4)

    def test_empty_dimensions_stay_empty(self) -> None:
        limited = limit_lengths({VOLUME: (15, 12, 0), ARPEGGIO: ()}, limit=ITEM_LIMIT)
        assert limited[ARPEGGIO] == ()

    def test_an_over_long_envelope_keeps_its_opening_items(self) -> None:
        limited = limit_lengths(volume_and_arpeggio(ITEM_LIMIT + 48), limit=ITEM_LIMIT)
        assert limited[VOLUME] == items_of(ITEM_LIMIT)
        assert len(limited[ARPEGGIO]) == ITEM_LIMIT

    def test_an_over_long_envelope_is_reported(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            limit_lengths(volume_and_arpeggio(ITEM_LIMIT + 1), limit=ITEM_LIMIT)

        assert str(ITEM_LIMIT) in caplog.text

    def test_an_envelope_within_the_limit_is_quiet(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            limit_lengths(volume_and_arpeggio(ITEM_LIMIT), limit=ITEM_LIMIT)

        assert caplog.text == ""


class TestItemLimit:
    @pytest.mark.parametrize("loop", [False, True], ids=["one_shot", "loop"])
    def test_an_over_long_envelope_keeps_its_opening_items(self, loop: bool) -> None:
        length = ITEM_LIMIT + 48

        equalized = equalize_lengths(volume_and_arpeggio(length), loop=loop, limit=ITEM_LIMIT)

        assert equalized[VOLUME] == items_of(ITEM_LIMIT)
        assert len(equalized[ARPEGGIO]) == ITEM_LIMIT

    def test_an_over_long_envelope_is_reported(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            equalize_lengths(volume_and_arpeggio(ITEM_LIMIT + 1), loop=False, limit=ITEM_LIMIT)

        assert str(ITEM_LIMIT) in caplog.text

    def test_an_envelope_within_the_limit_is_quiet(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            equalize_lengths(volume_and_arpeggio(ITEM_LIMIT), loop=False, limit=ITEM_LIMIT)

        assert caplog.text == ""


class TestUnboundedFormat:
    def test_an_absent_limit_keeps_every_item(self) -> None:
        length = ITEM_LIMIT + 48

        equalized = equalize_lengths(volume_and_arpeggio(length), loop=False)

        assert equalized[VOLUME] == items_of(length)
        assert len(equalized[ARPEGGIO]) == length

    def test_an_absent_limit_is_quiet(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            equalize_lengths(volume_and_arpeggio(ITEM_LIMIT + 1), loop=False)

        assert caplog.text == ""
