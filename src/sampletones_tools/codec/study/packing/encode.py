from time import process_time
from typing import Final, FrozenSet, Sequence, Tuple

from sampletones_player.compression.decode import decode_plane
from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.encode import encode_streams
from sampletones_player.compression.options import EVERY_LAYER, CodecOptions
from sampletones_player.specification.song import SONG_HEADER_SIZE
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.measure import Encoding
from sampletones_tools.codec.study.packing.coding import PlaneCoding
from sampletones_tools.codec.study.packing.scheme import (
    PackingScheme,
    plane_codings,
    stated_bytes,
)
from sampletones_tools.codec.study.packing.symbols import pack_plane, unpack_plane

NO_LOOP_BOUNDARIES: Final[FrozenSet[int]] = frozenset()
IDLE_PLANE: Final[bytes] = b""


def packed_symbols(
    planes: Sequence[bytes],
    codings: Sequence[PlaneCoding],
) -> Tuple[bytes, ...]:
    """Each plane as the symbols it plays, a plane holding its seeded value taking none.

    Args:
        planes: The planes, in the order the song block writes them.
        codings: How each plane's byte divides.

    Returns:
        Tuple[bytes, ...]: The symbols per plane, an idle plane's empty so the block leaves it out.
    """
    return tuple(
        IDLE_PLANE if coding.idles(plane) else pack_plane(plane, coding, boundaries=NO_LOOP_BOUNDARIES)
        for plane, coding in zip(planes, codings, strict=True)
    )


def plays_back(
    planes: Sequence[bytes],
    codings: Sequence[PlaneCoding],
    symbols: Sequence[bytes],
    streams: Sequence[bytes],
    table: PhraseTable,
) -> bool:
    """Whether the streams read back as the ticks the planes play.

    Args:
        planes: The planes, in the order the song block writes them.
        codings: How each plane's byte divides.
        symbols: The symbols each plane was written from.
        streams: The token stream each plane was written as.
        table: The dictionary the tokens name.

    Returns:
        bool: Whether every plane comes back as it stands.
    """
    for plane, coding, packed, stream in zip(planes, codings, symbols, streams, strict=True):
        if not stream:
            if not coding.idles(plane):
                return False

            continue

        if unpack_plane(decode_plane(stream, table, len(packed)), coding) != plane:
            return False

    return True


def encode_packed(
    song: StudySong,
    scheme: PackingScheme,
    *,
    options: CodecOptions = EVERY_LAYER,
) -> Encoding:
    """Encodes a song whose planes carry a repeat count in the bits their register leaves alone.

    The planes are packed into symbols and the production codec reads those, so a token's count
    names symbols where it named ticks and a hold repeats the symbol the plane reached — the
    reach of every token multiplying by what its symbol counts.

    Args:
        song: The song to encode.
        scheme: Where each plane's division between value and count comes from.
        options: Which of the codec's layers the encoding is built from.

    Returns:
        Encoding: The encoding, the block's header grown by what the scheme states.
    """
    planes = tuple(song.planes.planes)
    codings = plane_codings(planes, scheme)
    symbols = packed_symbols(planes, codings)

    started = process_time()
    table, streams = encode_streams(
        symbols,
        (),
        options=options,
        boundaries=(NO_LOOP_BOUNDARIES,) * len(symbols),
    )
    seconds = process_time() - started

    return Encoding(
        header=SONG_HEADER_SIZE + stated_bytes(codings, scheme),
        phrases=len(table),
        dictionary=table.size,
        streams=tuple(len(stream) for stream in streams),
        seconds=seconds,
        lossless=plays_back(planes, codings, symbols, streams, table),
        written=None,
    )
