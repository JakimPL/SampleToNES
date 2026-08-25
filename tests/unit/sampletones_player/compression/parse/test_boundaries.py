from typing import FrozenSet

from sampletones_player.compression.parse.boundaries import Boundaries

TICKS: int = 10
ENTRIES: FrozenSet[int] = frozenset({0, 4})


class TestWhereATokenMayStartAndHowFarItReaches:
    """A loop re-enters the stream partway through, so nothing spans the tick it re-enters at."""

    def test_the_entries_are_the_ticks_a_token_starts_on(self) -> None:
        assert Boundaries.across(TICKS, ENTRIES).entries == ENTRIES

    def test_a_tick_looks_back_to_the_boundary_behind_it(self) -> None:
        boundaries = Boundaries.across(TICKS, ENTRIES)
        assert boundaries.previous[6] == 4

    def test_a_tick_before_any_boundary_looks_back_to_the_start(self) -> None:
        boundaries = Boundaries.across(TICKS, ENTRIES)
        assert boundaries.previous[3] == 0

    def test_a_tick_looks_forward_to_the_boundary_ahead_of_it(self) -> None:
        boundaries = Boundaries.across(TICKS, ENTRIES)
        assert boundaries.following[0] == 4

    def test_a_tick_past_the_last_boundary_looks_forward_to_the_end_of_the_plane(self) -> None:
        boundaries = Boundaries.across(TICKS, ENTRIES)
        assert boundaries.following[4] == TICKS
