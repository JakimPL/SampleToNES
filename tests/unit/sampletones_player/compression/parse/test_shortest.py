import pytest

from sampletones_player.compression.parse.shortest import Shortest


class TestTheCheapestPathOverAnyTokens:
    """The search is the same over any grammar's tokens, which is what lets the codec study reuse it."""

    def test_the_cheapest_of_two_paths_is_walked(self) -> None:
        shortest: Shortest[str] = Shortest.across(3)
        shortest.relax(0, 3, 9, "whole")
        shortest.relax(0, 1, 2, "first")
        shortest.relax(1, 3, 3, "rest")

        assert shortest.walk(3) == ("first", "rest")

    def test_a_tie_keeps_the_way_found_first(self) -> None:
        shortest: Shortest[str] = Shortest.across(2)
        shortest.relax(0, 2, 4, "found first")
        shortest.relax(0, 2, 4, "found later")

        assert shortest.walk(2) == ("found first",)

    def test_a_dearer_way_found_later_leaves_the_cheaper_one(self) -> None:
        shortest: Shortest[int] = Shortest.across(1)
        shortest.relax(0, 1, 1, 10)
        shortest.relax(0, 1, 5, 20)

        assert (shortest.walk(1), shortest.costs[1]) == ((10,), 1)

    def test_a_plane_of_no_ticks_walks_no_tokens(self) -> None:
        assert Shortest.across(0).walk(0) == ()

    def test_a_tick_left_unreached_is_reported(self) -> None:
        shortest: Shortest[str] = Shortest.across(3)
        shortest.relax(0, 1, 1, "first")

        with pytest.raises(ValueError):
            shortest.walk(3)

    def test_improves_reads_an_unreached_tick_as_open_to_any_cost(self) -> None:
        shortest: Shortest[str] = Shortest.across(2)
        assert shortest.improves(2, 1_000)
        shortest.relax(0, 2, 5, "token")
        assert not shortest.improves(2, 5)
        assert shortest.improves(2, 4)
