from typing import Final, Tuple

import pytest

from sampletones_player.compression.dictionary.defaults import modal_counts
from sampletones_player.specification.compression import NO_DEFAULT_COUNT

PHRASES: Final[int] = 3


class TestThePhrasesDefaultCount:
    """A phrase defaults to the count its tokens play it at most often, so the most tokens leave it
    unstated; a tie goes to the shorter count, and a phrase never played has no default."""

    def test_the_most_frequent_count_wins(self) -> None:
        assert modal_counts([(0, 4), (0, 4), (0, 7)], PHRASES)[0] == 4

    def test_a_tie_goes_to_the_shorter_count(self) -> None:
        assert modal_counts([(0, 9), (0, 2), (0, 9), (0, 2)], PHRASES)[0] == 2

    def test_a_phrase_never_played_keeps_no_default(self) -> None:
        assert modal_counts([(1, 5)], PHRASES) == (NO_DEFAULT_COUNT, 5, NO_DEFAULT_COUNT)

    def test_no_plays_leave_every_phrase_without_a_default(self) -> None:
        assert modal_counts([], PHRASES) == (NO_DEFAULT_COUNT,) * PHRASES

    def test_an_empty_table_states_no_counts(self) -> None:
        assert modal_counts([], 0) == ()

    def test_the_counts_are_read_once_from_a_single_pass_iterable(self) -> None:
        plays = iter([(2, 3), (2, 3), (2, 1)])
        assert modal_counts(plays, PHRASES)[2] == 3

    def test_a_play_naming_a_phrase_beyond_the_table_is_refused(self) -> None:
        with pytest.raises(IndexError):
            modal_counts([(PHRASES, 1)], PHRASES)

    @pytest.mark.parametrize("plays", [((0, 1),) * 5 + ((0, 2),) * 4, ((1, 8),) * 2 + ((1, 3),) * 2])
    def test_the_count_chosen_is_one_the_tokens_play(self, plays: Tuple[Tuple[int, int], ...]) -> None:
        counts = modal_counts(plays, PHRASES)
        for phrase_id in {played_id for played_id, _ in plays}:
            assert counts[phrase_id] in {played for played_id, played in plays if played_id == phrase_id}
