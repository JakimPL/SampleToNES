from itertools import chain
from typing import Dict, Final, Iterator, List, Tuple

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.match import PhraseMatch
from sampletones_player.compression.matches.played import played_ticks
from sampletones_player.compression.matches.shift import translation
from sampletones_player.specification.compression import BYTE_VALUES

KEY_LENGTH: Final[int] = 2
MIN_PHRASE_TICKS: Final[int] = 2


class PhraseMatcher:
    """Answers which phrases a plane plays at a position, and for how many ticks.

    Phrases are held under the first steps of their shape, so a position offers a handful of
    candidates to confirm rather than the whole dictionary. A candidate confirms at the shift its
    first value asks for, which is the one shift that can possibly match there.

    A phrase is offered where the plane plays enough of it for those steps to tell it apart,
    which is a tick longer than the shortlist's key. A note cut shorter than that is spelled out,
    where a phrase token and a literal cost the same anyway.
    """

    def __init__(self, table: PhraseTable) -> None:
        self._bodies: Tuple[bytes, ...] = tuple(phrase.body for phrase in table.phrases)
        self._keyed: Dict[bytes, Tuple[int, ...]] = {}
        short: List[int] = []
        for phrase_id, phrase in enumerate(table.phrases):
            differences = phrase.differences
            if len(differences) < KEY_LENGTH:
                short.append(phrase_id)
                continue

            key = differences[:KEY_LENGTH]
            self._keyed[key] = self._keyed.get(key, ()) + (phrase_id,)

        self._short: Tuple[int, ...] = tuple(short)

    def matches(
        self,
        index: PlaneIndex,
        position: int,
        limit: int,
        *,
        transposition: bool,
    ) -> Iterator[PhraseMatch]:
        """Every phrase the plane plays from ``position``, with the ticks and shift it plays at.

        Args:
            index: The plane and the two readings of it matching is decided against.
            position: The tick the phrase would start at.
            limit: The most ticks a token may cover from there.
            transposition: Whether a phrase may play at a shift.

        Yields:
            PhraseMatch: The phrase, the ticks it covers and the shift it plays at.
        """
        if limit < MIN_PHRASE_TICKS:
            return

        origin = index.plane[position]
        key = index.differences[position : position + KEY_LENGTH]
        for phrase_id in chain(self._keyed.get(key, ()), self._short):
            body = self._bodies[phrase_id]
            transpose = (origin - body[0]) % BYTE_VALUES
            if transpose and not transposition:
                continue

            expected = body.translate(translation(transpose))
            ticks = played_ticks(
                index,
                position,
                expected,
                limit,
            )
            if ticks >= MIN_PHRASE_TICKS:
                yield PhraseMatch(
                    phrase_id=phrase_id,
                    ticks=ticks,
                    transpose=transpose,
                )
