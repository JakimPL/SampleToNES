from typing import List

import pytest

from sampletones_shared.utils.text import natural_sort_key


class TestNumbers:
    @pytest.mark.parametrize(
        ("names", "expected"),
        [
            (["44.1 kHz", "8 kHz"], ["8 kHz", "44.1 kHz"]),
            (["track10", "track2"], ["track2", "track10"]),
            (["10", "9", "100"], ["9", "10", "100"]),
            (["γ10", "γ2"], ["γ2", "γ10"]),
        ],
    )
    def test_digit_runs_compare_as_numbers(
        self,
        names: List[str],
        expected: List[str],
    ) -> None:
        assert sorted(names, key=natural_sort_key) == expected

    def test_leading_zeros_keep_a_fixed_order(self) -> None:
        """``01`` and ``1`` state the same number, and the text itself settles which reads first."""
        assert sorted(["1", "01"], key=natural_sort_key) == ["01", "1"]

    def test_a_number_reads_before_the_text_beside_it(self) -> None:
        assert sorted(["kick", "2 kick"], key=natural_sort_key) == ["2 kick", "kick"]


class TestText:
    def test_case_states_nothing_about_order(self) -> None:
        assert sorted(["Beats", "amen", "Cymbals"], key=natural_sort_key) == ["amen", "Beats", "Cymbals"]

    def test_names_reading_alike_keep_a_fixed_order(self) -> None:
        assert sorted(["song", "Song"], key=natural_sort_key) == ["Song", "song"]

    def test_a_shorter_name_reads_first(self) -> None:
        assert sorted(["amen breaks", "amen"], key=natural_sort_key) == ["amen", "amen breaks"]

    def test_the_empty_name_reads_first(self) -> None:
        assert sorted(["", "a"], key=natural_sort_key) == ["", "a"]


class TestKey:
    def test_one_name_reaches_one_key(self) -> None:
        assert natural_sort_key("44.1 kHz") == natural_sort_key("44.1 kHz")

    def test_a_name_the_reader_alone_can_spell(self) -> None:
        """A digit-like glyph outside the decimal digits is text, and the key states it as text."""
        assert sorted(["m²", "m1"], key=natural_sort_key) == ["m1", "m²"]
