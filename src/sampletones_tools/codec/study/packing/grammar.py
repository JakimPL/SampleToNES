from dataclasses import replace
from time import process_time
from typing import Tuple

from sampletones_player.compression.absent import is_absent
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.encode import encode_streams
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.measure import Encoding
from sampletones_tools.codec.study.packing.encode import NO_LOOP_BOUNDARIES, packed_symbols
from sampletones_tools.codec.study.packing.scheme import (
    PackingScheme,
    plane_codings,
    stated_bytes,
)
from sampletones_tools.codec.study.sandbox.defaults import no_defaults
from sampletones_tools.codec.study.sandbox.encode import encode_grammar
from sampletones_tools.codec.study.sandbox.grammar import BASELINE_GRAMMAR, Grammar
from sampletones_tools.codec.study.sandbox.reference import Reference, plane_parses
from sampletones_tools.codec.study.sandbox.verify import verify_baseline


def packed_reference(
    song: StudySong,
    scheme: PackingScheme,
) -> Tuple[Reference, int]:
    """A song's packed planes as every grammar is priced against them.

    The production codec settles a dictionary over the packed symbols, and the sandbox's
    baseline grammar is held to the streams it wrote, exactly as it is over a song's own
    planes. A grammar is then read on those streams alone.

    Args:
        song: The song.
        scheme: Where each plane's division between value and count comes from.

    Returns:
        Tuple[Reference, int]: What the grammars are priced against, and the bytes the block's
            header takes under the scheme.

    Raises:
        ValueError: If the baseline grammar prices a packed plane differently from the stream
            the codec wrote.
    """
    planes = tuple(song.planes.planes)
    codings = plane_codings(planes, scheme)
    symbols = packed_symbols(planes, codings)
    table, streams = encode_streams(
        symbols,
        (),
        options=EVERY_LAYER,
        boundaries=(NO_LOOP_BOUNDARIES,) * len(symbols),
    )
    compressed = CompressedPlanes(
        phrases=table,
        streams=PlaneOrder.across(streams),
        ticks=song.ticks,
    )
    cache = MatchCache(PlaneIndex.from_plane(plane) for plane in symbols if not is_absent(plane))
    baseline = plane_parses(symbols, cache, table, BASELINE_GRAMMAR, no_defaults(len(table)))
    verify_baseline(baseline, compressed)
    return (
        Reference(
            song=song,
            planes=symbols,
            table=table,
            cache=cache,
            baseline=baseline,
        ),
        SONG_HEADER_SIZE + stated_bytes(codings, scheme),
    )


def encode_packed_grammar(
    song: StudySong,
    scheme: PackingScheme,
    grammar: Grammar,
) -> Encoding:
    """Prices a song's packed planes under a grammar, over the dictionary the codec settled on.

    Args:
        song: The song to encode.
        scheme: Where each plane's division between value and count comes from.
        grammar: The grammar.

    Returns:
        Encoding: The bytes each stream would take, timed, and whether the tokens play back.
    """
    started = process_time()
    reference, header = packed_reference(song, scheme)
    priced = encode_grammar(reference, grammar)
    return replace(
        priced,
        header=header,
        seconds=process_time() - started,
    )
