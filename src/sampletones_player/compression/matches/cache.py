from array import array
from typing import Dict, Final, Iterable, List, Optional, Tuple

from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.played import played_ticks
from sampletones_player.compression.matches.reading import PhraseReading
from sampletones_player.compression.matches.shift import translation
from sampletones_player.specification.compression import BYTE_VALUES, MAX_PHRASE_TICKS

KEY_LENGTH: Final[int] = 2
TICKS_TYPECODE: Final[str] = "H"
TICKS_ENTRY_SIZE: Final[int] = 2
NO_MATCH: Final[int] = 0
MIN_PHRASE_TICKS: Final[int] = 2
NO_SHIFT: Final[int] = 0


class MatchCache:
    """What each phrase plays against each plane, measured once for a whole encoding.

    A phrase's match at a tick follows from the plane and the phrase alone, so it holds for every
    parse the encoder runs: a search round adds one phrase and measures that one, while every
    phrase already in the table answers from the reading taken when it arrived. This is what
    turns the cost of encoding from the parses times the dictionary into the dictionary alone.

    Each reading is taken against the most ticks a token could ever cover from that position, and
    a parse reading it under a shorter reach takes the smaller of the two — the same answer
    measuring again would give, since a phrase matches for as long as the plane agrees with it
    and a shorter reach only cuts that agreement short.

    Positions are offered to a phrase by its first steps, the way the shortlist offers them, so a
    reading covers the ticks the phrase could begin at rather than every tick of the plane.
    """

    def __init__(self, indices: Iterable[PlaneIndex]) -> None:
        self._indices: Tuple[PlaneIndex, ...] = tuple(indices)
        self._offers: List[Optional[Dict[bytes, Tuple[int, ...]]]] = [None] * len(self._indices)
        self._readings: Dict[Tuple[int, bytes], PhraseReading] = {}

    @property
    def indices(self) -> Tuple[PlaneIndex, ...]:
        """The planes the encoding covers, in song-block order."""
        return self._indices

    def index(self, plane: int) -> PlaneIndex:
        """The plane at ``plane`` and the readings of it matching is decided against.

        Args:
            plane: The plane's position in song-block order.

        Returns:
            PlaneIndex: The plane, its steps and its runs.
        """
        return self._indices[plane]

    def reading(self, plane: int, phrase: Phrase) -> PhraseReading:
        """What ``phrase`` plays against ``plane``, measured on first ask and kept thereafter.

        Args:
            plane: The plane's position in song-block order.
            phrase: The phrase the plane is read against.

        Returns:
            PhraseReading: The ticks played from each position, and whether the plane plays the
                phrase at all.
        """
        entry = (plane, phrase.body)
        measured = self._readings.get(entry)
        if measured is None:
            measured = self._measure(plane, phrase)
            self._readings[entry] = measured

        return measured

    def _measure(self, plane: int, phrase: Phrase) -> PhraseReading:
        index = self._indices[plane]
        body = phrase.body
        origin = body[0]
        measured = array(TICKS_TYPECODE, bytes(TICKS_ENTRY_SIZE * index.ticks))
        shifted = False
        unshifted = False
        for position in self._offered(plane, phrase):
            transpose = (index.plane[position] - origin) % BYTE_VALUES
            ticks = played_ticks(
                index,
                position,
                body.translate(translation(transpose)),
                min(MAX_PHRASE_TICKS, index.ticks - position),
            )
            measured[position] = ticks
            if ticks >= MIN_PHRASE_TICKS:
                shifted = True
                unshifted = unshifted or transpose == NO_SHIFT

        return PhraseReading(ticks=measured, shifted=shifted, unshifted=unshifted)

    def _offered(self, plane: int, phrase: Phrase) -> Iterable[int]:
        differences = phrase.differences
        if len(differences) < KEY_LENGTH:
            return range(self._indices[plane].ticks)

        return self._offers_by_key(plane).get(differences[:KEY_LENGTH], ())

    def _offers_by_key(self, plane: int) -> Dict[bytes, Tuple[int, ...]]:
        cached = self._offers[plane]
        if cached is not None:
            return cached

        index = self._indices[plane]
        differences = index.differences
        gathered: Dict[bytes, List[int]] = {}
        for position in range(index.ticks):
            gathered.setdefault(differences[position : position + KEY_LENGTH], []).append(position)

        offers = {key: tuple(positions) for key, positions in gathered.items()}
        self._offers[plane] = offers
        return offers
