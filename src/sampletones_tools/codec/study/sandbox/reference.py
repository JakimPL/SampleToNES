from dataclasses import dataclass
from typing import Final, FrozenSet, Sequence, Tuple

from sampletones_player.compression.absent import is_absent
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.encode import STREAM_START
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.parse.boundaries import Boundaries
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.sandbox.context import PlaneContext
from sampletones_tools.codec.study.sandbox.costs import Costs
from sampletones_tools.codec.study.sandbox.defaults import no_defaults
from sampletones_tools.codec.study.sandbox.grammar import BASELINE_GRAMMAR, Grammar
from sampletones_tools.codec.study.sandbox.parse import StudyParse, parse_plane
from sampletones_tools.codec.study.sandbox.verify import verify_baseline

STREAM_ENTRIES: Final[FrozenSet[int]] = frozenset({STREAM_START})
ABSENT_PARSE: Final[StudyParse] = StudyParse(tokens=(), costs=(0,))


@dataclass(frozen=True)
class Reference:
    """One song as every grammar is priced against it.

    The dictionary is the one the production codec settled on, held fixed across the grammars:
    what a grammar earns is read on the streams alone, and how the search and the settling
    would answer a new grammar is left to its production layer to measure.

    An absent plane takes no stream in production, so it takes no tokens under any grammar and
    the cache holds the planes the block writes alone.

    Attributes:
        song: The song.
        table: The dictionary the production codec settled on.
        cache: What each phrase plays against each written plane, shared by every grammar's parse.
        baseline: Every plane under the baseline grammar, held to the production streams.
    """

    song: StudySong
    table: PhraseTable
    cache: MatchCache
    baseline: Tuple[StudyParse, ...]

    def parses(
        self,
        grammar: Grammar,
        defaults: Sequence[int],
    ) -> Tuple[StudyParse, ...]:
        """Every plane of the song read under one grammar.

        Args:
            grammar: The grammar.
            defaults: The default count of each phrase, by id.

        Returns:
            Tuple[StudyParse, ...]: One parse per plane, in song-block order, an absent plane's empty.
        """
        return _parses(self.song, self.cache, self.table, grammar, defaults)


def _contexts(
    cache: MatchCache,
    table: PhraseTable,
    costs: Costs,
    defaults: Sequence[int],
) -> Tuple[PlaneContext, ...]:
    contexts = []
    for plane, index in enumerate(cache.indices):
        contexts.append(
            PlaneContext(
                index=index,
                matcher=PhraseMatcher(table, plane, cache),
                boundaries=Boundaries.across(index.ticks, STREAM_ENTRIES),
                transposition=EVERY_LAYER.transposition,
                defaults=tuple(defaults),
                costs=costs,
            )
        )

    return tuple(contexts)


def _parses(
    song: StudySong,
    cache: MatchCache,
    table: PhraseTable,
    grammar: Grammar,
    defaults: Sequence[int],
) -> Tuple[StudyParse, ...]:
    written = iter(parse_plane(context, grammar) for context in _contexts(cache, table, grammar.costs, defaults))
    return tuple(ABSENT_PARSE if is_absent(plane) else next(written) for plane in song.planes.planes)


def reference(
    song: StudySong,
    compressed: CompressedPlanes,
) -> Reference:
    """Reads a song into what every grammar is priced against, proving the parser on the way.

    Args:
        song: The song.
        compressed: The production encoding of the song.

    Returns:
        Reference: The song, its dictionary, its matches and its baseline parse.

    Raises:
        ValueError: If the baseline grammar prices a plane differently from the codec's stream.
    """
    cache = MatchCache(PlaneIndex.from_plane(plane) for plane in song.planes.planes if not is_absent(plane))
    table = compressed.phrases
    baseline = _parses(song, cache, table, BASELINE_GRAMMAR, no_defaults(len(table)))
    verify_baseline(baseline, compressed)
    return Reference(
        song=song,
        table=table,
        cache=cache,
        baseline=baseline,
    )
