from dataclasses import dataclass
from typing import Final, FrozenSet, Sequence, Tuple

from codec_study.corpus.song import StudySong
from codec_study.sandbox.context import PlaneContext
from codec_study.sandbox.costs import PRODUCTION_COSTS, Costs
from codec_study.sandbox.defaults import no_defaults
from codec_study.sandbox.grammar import BASELINE_GRAMMAR
from codec_study.sandbox.parse import StudyParse, parse_plane
from codec_study.sandbox.verify import verify_baseline
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.encode import STREAM_START
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.parse.boundaries import Boundaries

STREAM_ENTRIES: Final[FrozenSet[int]] = frozenset({STREAM_START})


@dataclass(frozen=True)
class Reference:
    """One song as every grammar is priced against it.

    The dictionary is the one the production codec settled on, held fixed across the grammars:
    what a grammar earns is read on the streams alone, and how the search and the settling
    would answer a new grammar is left to its production layer to measure.

    Attributes:
        song: The song.
        table: The dictionary the production codec settled on.
        cache: What each phrase plays against each plane, shared by every grammar's parse.
        baseline: Every plane under the baseline grammar, held to the production streams.
    """

    song: StudySong
    table: PhraseTable
    cache: MatchCache
    baseline: Tuple[StudyParse, ...]

    def contexts(
        self,
        costs: Costs,
        defaults: Sequence[int],
    ) -> Tuple[PlaneContext, ...]:
        """Every plane of the song under one grammar's terms.

        Args:
            costs: The bytes each token takes.
            defaults: The default count of each phrase, by id.

        Returns:
            Tuple[PlaneContext, ...]: One context per plane, in song-block order.
        """
        return _contexts(self.cache, self.table, costs, defaults)


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
    cache = MatchCache(PlaneIndex.from_plane(plane) for plane in song.planes.planes)
    table = compressed.phrases
    contexts = _contexts(cache, table, PRODUCTION_COSTS, no_defaults(len(table)))
    baseline = tuple(parse_plane(context, BASELINE_GRAMMAR) for context in contexts)
    verify_baseline(baseline, compressed)
    return Reference(
        song=song,
        table=table,
        cache=cache,
        baseline=baseline,
    )
