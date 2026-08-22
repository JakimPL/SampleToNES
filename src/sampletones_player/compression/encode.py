from dataclasses import replace
from typing import Dict, Final, FrozenSet, Iterable, Sequence, Tuple

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.prune import prune
from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.parse.song import parse_planes
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.search import search_phrases
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.types import TokenUnion
from sampletones_player.specification.compression import PHRASE_ID_ESCAPE, TokenTag

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
                stream.append(tag | named)
                if named == PHRASE_ID_ESCAPE:
                    stream.append(token.phrase_id)

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


def _settle(
    cache: MatchCache,
    table: PhraseTable,
    options: CodecOptions,
    boundaries: FrozenSet[int],
) -> Tuple[PhraseTable, Tuple[Parse, ...]]:
    baseline = parse_planes(
        cache,
        phrase_table(()),
        replace(options, phrases=False),
        boundaries,
    )
    parses = parse_planes(cache, table, options, boundaries)
    for _ in range(SETTLING_ROUNDS):
        pruned = prune(
            table,
            _references(parses, len(table)),
            _savings(parses, baseline, len(table)),
        )
        if pruned.phrases == table.phrases:
            break

        table = pruned
        parses = parse_planes(cache, table, options, boundaries)

    return table, parses


def encode_planes(
    planes: SongPlanes,
    seeds: Sequence[Phrase],
    *,
    options: CodecOptions,
    boundaries: FrozenSet[int],
) -> CompressedPlanes:
    """Compresses a song's eight planes into the dictionary and streams the driver reads.

    The instruments seed the dictionary, the search fills what they leave behind, and the table
    then settles: phrases the parse names keep their place in the order they are leaned on, and
    the parse runs again over the ids that frees, which is what puts the busiest phrases inside
    the opcodes that name them.

    Args:
        planes: The eight planes, two per channel.
        seeds: The phrases the song's instruments offer.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on, beyond the first tick of the song.

    Returns:
        CompressedPlanes: The dictionary, the eight token streams and the ticks the song lasts.
    """
    cache = MatchCache(PlaneIndex.from_plane(plane) for plane in planes.planes)
    entries = boundaries | {STREAM_START}
    table = phrase_table(seeds) if options.phrases else phrase_table(())
    if options.phrases and options.search:
        table = search_phrases(cache, table, options, entries)

    table, parses = _settle(cache, table, options, entries)
    return CompressedPlanes(
        phrases=table,
        streams=PlaneOrder.across(emit(parse.tokens) for parse in parses),
        ticks=planes.ticks,
    )
