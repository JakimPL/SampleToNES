from dataclasses import dataclass
from typing import Final, FrozenSet, Sequence, Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.encode import STREAM_START
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.parse.boundaries import Boundaries
from sampletones_player.compression.planes.symbols import pack_plane
from sampletones_player.specification.planes import PLANES, SINGLE_TICK
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.sandbox.context import PlaneContext
from sampletones_tools.codec.study.sandbox.costs import Costs
from sampletones_tools.codec.study.sandbox.grammar import BASELINE_GRAMMAR, Grammar
from sampletones_tools.codec.study.sandbox.parse import StudyParse, parse_plane
from sampletones_tools.codec.study.sandbox.verify import verify_baseline

STREAM_ENTRIES: Final[FrozenSet[int]] = frozenset({STREAM_START})
NO_BOUNDARIES: Final[FrozenSet[int]] = frozenset()
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
        planes: The byte series each stream was written from, in song-block order.
        table: The dictionary the production codec settled on.
        cache: What each phrase plays against each written plane, shared by every grammar's parse.
        seeds: The symbol each written plane stands at before its first token.
        baseline: Every plane under the baseline grammar, held to the production streams.
    """

    song: StudySong
    planes: Tuple[bytes, ...]
    table: PhraseTable
    cache: MatchCache
    seeds: Tuple[int, ...]
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
        return plane_parses(self.planes, self.cache, self.table, grammar, defaults, self.seeds)


def _contexts(
    cache: MatchCache,
    table: PhraseTable,
    costs: Costs,
    defaults: Sequence[int],
    seeds: Sequence[int],
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
                seeded=seeds[plane],
                costs=costs,
            )
        )

    return tuple(contexts)


def plane_parses(
    planes: Sequence[bytes],
    cache: MatchCache,
    table: PhraseTable,
    grammar: Grammar,
    defaults: Sequence[int],
    seeds: Sequence[int],
) -> Tuple[StudyParse, ...]:
    contexts = _contexts(cache, table, grammar.costs, defaults, seeds)
    written = iter(parse_plane(context, grammar) for context in contexts)
    return tuple(next(written) if plane else ABSENT_PARSE for plane in planes)


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
    planes = tuple(
        b"" if plane.idles(played) else pack_plane(played, plane.form, boundaries=NO_BOUNDARIES)
        for plane, played in zip(PLANES, song.planes.planes, strict=True)
    )
    cache = MatchCache(PlaneIndex.from_plane(plane) for plane in planes if plane)
    seeds = tuple(
        plane.form.symbol(plane.seeded, SINGLE_TICK) for plane, written in zip(PLANES, planes, strict=True) if written
    )
    table = compressed.phrases
    carried = tuple(phrase.default for phrase in table.phrases)
    baseline = plane_parses(planes, cache, table, BASELINE_GRAMMAR, carried, seeds)
    verify_baseline(baseline, compressed)
    return Reference(
        song=song,
        planes=planes,
        table=table,
        cache=cache,
        seeds=seeds,
        baseline=baseline,
    )
