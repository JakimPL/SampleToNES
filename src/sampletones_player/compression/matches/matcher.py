from itertools import chain
from typing import Dict, Iterator, List, Sequence, Tuple

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.matches.cache import KEY_LENGTH, MIN_PHRASE_TICKS, MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.match import PhraseMatch
from sampletones_player.specification.compression import BYTE_VALUES


class PhraseMatcher:
    """Answers which phrases one plane plays at a tick, and for how many ticks.

    Phrases are held under the first steps of their shape, so a position offers a handful of
    candidates rather than the whole dictionary. A candidate plays at the shift its first value
    asks for, which is the one shift that can possibly match there, and the ticks it plays for
    are read from the cache the whole encoding shares.

    A phrase is offered where the plane plays enough of it for those steps to tell it apart,
    which is a tick longer than the shortlist's key. A note cut shorter than that is spelled out,
    where a phrase token and a literal cost the same anyway.

    A matcher answers for the one plane it was built against, so the plane and the dictionary it
    is read under arrive together and stay together.
    """

    def __init__(
        self,
        table: PhraseTable,
        plane: int,
        cache: MatchCache,
    ) -> None:
        self._index: PlaneIndex = cache.index(plane)
        self._origins: Tuple[int, ...] = tuple(phrase.body[0] for phrase in table.phrases)
        self._played: Tuple[Sequence[int], ...] = tuple(cache.reading(plane, phrase).ticks for phrase in table.phrases)
        keyed: Dict[bytes, List[int]] = {}
        short: List[int] = []
        for phrase_id, phrase in enumerate(table.phrases):
            differences = phrase.differences
            if len(differences) < KEY_LENGTH:
                short.append(phrase_id)
                continue

            keyed.setdefault(differences[:KEY_LENGTH], []).append(phrase_id)

        self._keyed: Dict[bytes, Tuple[int, ...]] = {key: tuple(ids) for key, ids in keyed.items()}
        self._short: Tuple[int, ...] = tuple(short)

    @property
    def index(self) -> PlaneIndex:
        """The plane the matcher answers for, and the readings of it matching is decided against."""
        return self._index

    def matches(
        self,
        position: int,
        limit: int,
        *,
        transposition: bool,
    ) -> Iterator[PhraseMatch]:
        """Every phrase the plane plays from ``position``, with the ticks and shift it plays at.

        Args:
            position: The tick the phrase would start at.
            limit: The most ticks a token may cover from there.
            transposition: Whether a phrase may play at a shift.

        Yields:
            PhraseMatch: The phrase, the ticks it covers and the shift it plays at.
        """
        if limit < MIN_PHRASE_TICKS:
            return

        index = self._index
        origin = index.plane[position]
        key = index.differences[position : position + KEY_LENGTH]
        for phrase_id in chain(self._keyed.get(key, ()), self._short):
            transpose = (origin - self._origins[phrase_id]) % BYTE_VALUES
            if transpose and not transposition:
                continue

            ticks = min(self._played[phrase_id][position], limit)
            if ticks >= MIN_PHRASE_TICKS:
                yield PhraseMatch(
                    phrase_id=phrase_id,
                    ticks=ticks,
                    transpose=transpose,
                )
