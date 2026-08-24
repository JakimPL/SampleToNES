from typing import Optional, Tuple

import pytest

from sampletones_core.features.envelope import Envelope
from sampletones_core.features.text import format_envelope, parse_envelope


class TestWhatAReaderTypes:
    @pytest.mark.parametrize(
        ("text", "items", "loop_point"),
        [
            ("15 14 12 10", (15, 14, 12, 10), None),
            ("15 14 | 12 10", (15, 14, 12, 10), 2),
            ("| 15 14", (15, 14), 0),
            ("0", (0,), None),
            ("", (), None),
            ("  15   14  ", (15, 14), None),
            ("-4 0 7", (-4, 0, 7), None),
        ],
    )
    def test_a_typed_sequence_states_its_values_and_the_item_they_repeat_from(
        self,
        text: str,
        items: Tuple[int, ...],
        loop_point: Optional[int],
    ) -> None:
        envelope = parse_envelope(text)

        assert (envelope.items, envelope.loop_point) == (items, loop_point)

    def test_the_point_names_the_item_it_stands_before(self) -> None:
        """A reader places the bar where the sequence turns back, and that item is what plays next."""
        envelope = parse_envelope("15 14 | 12 10")

        assert envelope.at(4) == 12

    @pytest.mark.parametrize(
        "text",
        [
            "15 | 14 | 12",
            "15 14 |",
            "|",
            "15 x 14",
            "15 1.5",
            "15 -",
        ],
    )
    def test_a_sequence_that_states_no_dimension_is_refused(self, text: str) -> None:
        with pytest.raises(ValueError):
            parse_envelope(text)


class TestWhatAReaderIsShown:
    @pytest.mark.parametrize(
        ("items", "loop_point", "text"),
        [
            ((15, 14, 12, 10), None, "15 14 12 10"),
            ((15, 14, 12, 10), 2, "15 14 | 12 10"),
            ((15, 14), 0, "| 15 14"),
            ((15, 14), 1, "15 | 14"),
            ((), None, ""),
        ],
    )
    def test_a_dimension_is_written_out_as_it_would_be_typed(
        self,
        items: Tuple[int, ...],
        loop_point: Optional[int],
        text: str,
    ) -> None:
        assert format_envelope(Envelope[int](items=items, loop_point=loop_point)) == text

    @pytest.mark.parametrize(
        "text",
        ["15 14 12 10", "15 14 | 12 10", "| 15 14", ""],
    )
    def test_what_is_shown_reads_back_as_what_it_shows(self, text: str) -> None:
        assert format_envelope(parse_envelope(text)) == text
