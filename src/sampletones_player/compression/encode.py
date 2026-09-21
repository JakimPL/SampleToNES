from collections import Counter
from dataclasses import replace
from typing import Dict, Final, FrozenSet, Iterable, List, Sequence, Tuple

from sampletones_player.compression.admit import admit_seeds
from sampletones_player.compression.budget import (
    DEFAULT_SEARCH_BUDGET,
    SearchBudget,
)
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.prune import prune
from sampletones_player.compression.dictionary.table import (
    PhraseTable,
    phrase_table,
)
from sampletones_player.compression.entries import stream_entry
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.parse.song import parse_planes
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.planes.symbols import (
    pack_plane,
    symbol_boundaries,
)
from sampletones_player.compression.progress.monitor import CodecMonitor
from sampletones_player.compression.progress.report import (
    CodecReporter,
)
from sampletones_player.compression.search import search_phrases
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.types import TokenUnion
from sampletones_player.specification.compression import (
    DEFAULT_COUNT_FLAG,
    NO_DEFAULT_COUNT,
    PHRASE_ID_ESCAPE,
    TokenTag,
)
from sampletones_player.specification.planes import PLANES
from sampletones_shared.utils.progress import silent_reporter

STREAM_START: Final[int] = 0
SETTLING_ROUNDS: Final[int] = 3


def emit(tokens: Sequence[TokenUnion]) -> bytes:
    """Writes a plane's tokens out as the bytes the driver reads them from.

    Args:
        tokens: The tokens the plane is written as, in the order they are read.

    Returns:
        bytes: The plane's token stream.
    """
    stream = bytearray()
    for token in tokens:
        match token:
            case HoldToken():
                stream.append(TokenTag.HOLD | (token.ticks - 1))
            case LiteralToken():
                stream.append(TokenTag.LITERAL | (len(token.values) - 1))
                stream.extend(token.values)
            case PhraseToken():
                tag = TokenTag.TRANSPOSED_PHRASE if token.transpose else TokenTag.PHRASE
                named = min(token.phrase_id, PHRASE_ID_ESCAPE)
                stream.append(tag | (DEFAULT_COUNT_FLAG if token.default else 0) | named)
                if named == PHRASE_ID_ESCAPE:
                    stream.append(token.phrase_id)

                if not token.default:
                    stream.append(token.ticks - 1)

                if token.transpose:
                    stream.append(token.transpose)

    return bytes(stream)


def _references(parses: Iterable[Parse], phrases: int) -> Dict[int, int]:
    references = {phrase_id: 0 for phrase_id in range(phrases)}
    for parse in parses:
        for token in parse.tokens:
            if isinstance(token, PhraseToken):
                references[token.phrase_id] += 1

    return references


def _savings(
    parses: Sequence[Parse],
    baseline: Sequence[Parse],
    phrases: int,
) -> Dict[int, int]:
    savings = {phrase_id: 0 for phrase_id in range(phrases)}
    for parse, plain in zip(parses, baseline):
        position = 0
        for token in parse.tokens:
            if isinstance(token, PhraseToken):
                spared = plain.costs[position + token.ticks] - plain.costs[position]
                savings[token.phrase_id] += spared - token.size

            position += token.ticks

    return savings


def _modal(played: Counter[int]) -> int:
    """The count a phrase's tokens play it at most often, the shortest breaking a tie."""
    if not played:
        return NO_DEFAULT_COUNT

    return min(played, key=lambda ticks: (-played[ticks], ticks))


def _counts(parses: Iterable[Parse], phrases: int) -> Dict[int, int]:
    """The count each phrase's tokens play it at most often, the shortest breaking a tie."""
    played: List[Counter[int]] = [Counter() for _ in range(phrases)]
    for parse in parses:
        for token in parse.tokens:
            if isinstance(token, PhraseToken):
                played[token.phrase_id][token.ticks] += 1

    return {phrase_id: _modal(counter) for phrase_id, counter in enumerate(played)}


def _settle(
    cache: MatchCache,
    table: PhraseTable,
    options: CodecOptions,
    boundaries: Sequence[FrozenSet[int]],
    monitor: CodecMonitor,
    baseline: Sequence[Parse],
) -> Tuple[PhraseTable, Tuple[Parse, ...]]:
    """The table and its parses settled together, each round reading the other.

    A phrase's place, its id and the count its tokens leave unstated are all read off a parse
    that was made under the table before it, so the table is rebuilt and the planes read again
    until the two stand still.
    """
    parses = parse_planes(cache, table, options, boundaries, monitor)
    for _ in range(SETTLING_ROUNDS):
        pruned = prune(
            table,
            _references(parses, len(table)),
            _savings(parses, baseline, len(table)),
            _counts(parses, len(table)),
        )
        if pruned.phrases == table.phrases:
            break

        table = pruned
        parses = parse_planes(cache, table, options, boundaries, monitor)
        monitor.reached(len(table), table.size + sum(parse.size for parse in parses))

    return table, parses


def encode_streams(
    planes: Sequence[bytes],
    seeds: Sequence[Phrase],
    *,
    options: CodecOptions,
    boundaries: Sequence[FrozenSet[int]],
    budget: SearchBudget = DEFAULT_SEARCH_BUDGET,
    report: CodecReporter = silent_reporter,
) -> Tuple[PhraseTable, Tuple[bytes, ...]]:
    """Compresses a run of planes into one dictionary and a token stream for each.

    Every layer is weighed against one reading of the planes naming no phrase at all: the seeds
    a dictionary crowded past its ids keeps, and the bytes each phrase spares once the table
    settles. The instruments seed the dictionary, the search fills what they leave behind, and
    the table then settles — phrases the parse names keep their place in the order they are
    leaned on, and the parse runs again over the ids that frees, which is what puts the busiest
    phrases inside the opcodes that name them.

    Each plane is read against the shared dictionary on its own, so the planes may cover
    different numbers of values. A plane reaching the encoder empty is absent: it takes no
    stream, and the block states it with a sentinel the driver skips.

    Args:
        planes: The planes, each at least one value long.
        seeds: The phrases the song's instruments offer.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The positions a token starts on in each plane beyond its first, one set per
            plane.
        budget: How much work the search spends beyond the phrases the instruments seed.
        report: Hears what the run holds each time it looks up, and answers whether it goes on.

    Returns:
        Tuple[PhraseTable, Tuple[bytes, ...]]: The dictionary, then each plane's token stream in
            the order the planes were given, an absent plane's empty.

    Raises:
        OperationCanceled: If ``report`` withdraws the run.
        ValueError: If the boundaries name a set for other than every plane.
    """
    if len(boundaries) != len(planes):
        raise ValueError(f"a set of boundaries stands for each plane, and {len(boundaries)} stand for {len(planes)}")

    present = [plane for plane, written in enumerate(planes) if written]
    cache = MatchCache(PlaneIndex.from_plane(planes[plane]) for plane in present)
    monitor = CodecMonitor(report)
    entries = tuple(boundaries[plane] | {STREAM_START} for plane in present)
    baseline = parse_planes(
        cache,
        phrase_table(()),
        replace(options, phrases=False),
        entries,
        monitor,
    )
    table = (
        admit_seeds(
            cache,
            seeds,
            baseline,
            options,
        )
        if options.phrases
        else phrase_table(())
    )
    if options.phrases and options.search:
        table = search_phrases(
            cache,
            table,
            options,
            entries,
            monitor,
            budget,
        )

    table, parses = _settle(
        cache,
        table,
        options,
        entries,
        monitor,
        baseline,
    )
    written = iter(emit(parse.tokens) for parse in parses)
    streams = tuple(next(written) if plane else b"" for plane in planes)
    monitor.reached(len(table), table.size + sum(len(stream) for stream in streams))
    return table, streams


def _returned(boundaries: FrozenSet[int]) -> int:
    """The tick a song comes round to, the song's first standing in where it plays once."""
    return min(boundaries, default=STREAM_START)


def encode_planes(
    planes: SongPlanes,
    seeds: Sequence[Phrase],
    *,
    options: CodecOptions,
    boundaries: FrozenSet[int],
    budget: SearchBudget = DEFAULT_SEARCH_BUDGET,
    report: CodecReporter = silent_reporter,
) -> CompressedPlanes:
    """Compresses a song's planes into the dictionary and streams the driver reads.

    Args:
        planes: The planes under the channel each belongs to.
        seeds: The phrases the song's instruments offer.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on, beyond the first tick of the song; a bend plane
            starts one at the position it stands at once those ticks have played.
        budget: How much work the search spends beyond the phrases the instruments seed.
        report: Hears what the run holds each time it looks up, and answers whether it goes on.

    Returns:
        CompressedPlanes: The dictionary, every plane's token stream and the ticks the song lasts.

    Raises:
        OperationCanceled: If ``report`` withdraws the run.
    """
    positions = [planes.positions(tick) for tick in boundaries]
    entries = [frozenset(position[index] for position in positions) for index in range(len(planes.planes))]
    packed = tuple(
        (b"" if plane.idles(played) else pack_plane(played, plane.form, boundaries=entry))
        for plane, played, entry in zip(PLANES, planes.planes, entries, strict=True)
    )
    table, streams = encode_streams(
        packed,
        seeds,
        options=options,
        boundaries=[
            symbol_boundaries(played, plane.form, boundaries=entry)
            for plane, played, entry in zip(PLANES, planes.planes, entries, strict=True)
        ],
        budget=budget,
        report=report,
    )
    returned = [
        symbol_boundaries(played, plane.form, boundaries=frozenset({position}))
        for plane, played, position in zip(
            PLANES,
            planes.planes,
            planes.positions(_returned(boundaries)),
            strict=True,
        )
    ]
    return CompressedPlanes(
        phrases=table,
        streams=PlaneOrder.across(streams),
        ticks=planes.ticks,
        loop_entries=tuple(
            (stream_entry(stream, next(iter(entry), STREAM_START), table) if stream else None)
            for stream, entry in zip(streams, returned, strict=True)
        ),
    )
