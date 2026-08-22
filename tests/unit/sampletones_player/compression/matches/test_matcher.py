from typing import Final, List, Tuple

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.compression.matches.cache import KEY_LENGTH, MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.match import PhraseMatch
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.specification.compression import MAX_PHRASE_TICKS

MOTIF: Final[bytes] = bytes((40, 44, 47))
SINGLE_PLANE: Final[int] = 0


def found(plane: bytes, phrases: Tuple[Phrase, ...], position: int) -> List[PhraseMatch]:
    cache = MatchCache((PlaneIndex.from_plane(plane),))
    matcher = PhraseMatcher(phrase_table(phrases), SINGLE_PLANE, cache)
    return list(
        matcher.matches(
            position,
            min(MAX_PHRASE_TICKS, len(plane) - position),
            transposition=True,
        )
    )


class TestWhichPhrasesAPlanePlays:
    """One dictionary entry serves every pitch and every length a figure is played at."""

    def test_a_phrase_matches_where_the_plane_plays_it(self) -> None:
        assert found(MOTIF, (Phrase(body=MOTIF),), 0) == [PhraseMatch(phrase_id=0, ticks=len(MOTIF), transpose=0)]

    def test_a_phrase_matches_the_same_figure_played_higher(self) -> None:
        higher = bytes(value + 5 for value in MOTIF)
        assert found(higher, (Phrase(body=MOTIF),), 0) == [PhraseMatch(phrase_id=0, ticks=len(MOTIF), transpose=5)]

    def test_a_phrase_matches_the_same_figure_played_lower(self) -> None:
        """A shift is added to a byte, so a fall reaches the token as the byte that wraps to it."""
        lower = bytes(value - 3 for value in MOTIF)
        assert found(lower, (Phrase(body=MOTIF),), 0) == [PhraseMatch(phrase_id=0, ticks=len(MOTIF), transpose=253)]

    def test_a_note_outlasting_its_phrase_holds_the_phrase_out(self) -> None:
        plane = MOTIF + bytes((MOTIF[-1],)) * 4
        assert found(plane, (Phrase(body=MOTIF),), 0) == [PhraseMatch(phrase_id=0, ticks=len(plane), transpose=0)]

    def test_a_note_cut_short_plays_as_much_of_the_phrase_as_sounded(self) -> None:
        plane = MOTIF[:3] + bytes((99,))
        assert found(plane, (Phrase(body=MOTIF),), 0) == [PhraseMatch(phrase_id=0, ticks=3, transpose=0)]

    def test_a_note_cut_before_its_shape_is_told_apart_is_offered_nowhere(self) -> None:
        """A phrase is shortlisted by its first steps, so a shorter start names no phrase."""
        plane = MOTIF[:KEY_LENGTH] + bytes((99,))
        assert found(plane, (Phrase(body=MOTIF),), 0) == []

    def test_a_figure_the_plane_never_plays_is_offered_nowhere(self) -> None:
        assert found(bytes((1, 9, 1)), (Phrase(body=MOTIF),), 0) == []

    def test_a_phrase_is_offered_wherever_the_plane_plays_it(self) -> None:
        plane = MOTIF + bytes((0,)) + MOTIF
        entered = found(plane, (Phrase(body=MOTIF),), len(MOTIF) + 1)
        assert entered == [PhraseMatch(phrase_id=0, ticks=len(MOTIF), transpose=0)]
