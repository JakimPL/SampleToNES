from time import process_time
from typing import Sequence, Tuple

from sampletones_player.compression.decode import decode_plane
from sampletones_player.compression.encode import encode_streams
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.specification.compression import INITIAL_PLANE_VALUE
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.layouts.layout import PlaneLayout
from sampletones_tools.codec.study.layouts.planes import layout_planes, layout_seeds
from sampletones_tools.codec.study.measure import Encoding
from sampletones_tools.codec.study.variants.production import NO_LOOP_BOUNDARIES


def is_absent(plane: bytes) -> bool:
    """Whether a plane holds nothing past the value every plane starts at, so the block omits it."""
    return set(plane) <= {INITIAL_PLANE_VALUE}


def encode_layout(
    song: StudySong,
    layout: PlaneLayout,
) -> Encoding:
    """Encodes a song's planes written under a layout, every layer of the production codec on.

    A plane holding the starting value throughout is left out of the block, which is how the
    driver will read a channel that never bends, so it costs no stream at all.

    Args:
        song: The song to encode.
        layout: How each tone channel's divider is written.

    Returns:
        Encoding: The encoding, an absent plane's stream counted as nothing.
    """
    planes = layout_planes(song, layout)
    present = tuple(plane for plane in planes if not is_absent(plane))
    seeds = layout_seeds(song.slices, song.pitches, layout)

    started = process_time()
    table, streams = encode_streams(
        present,
        seeds,
        options=EVERY_LAYER,
        boundaries=NO_LOOP_BOUNDARIES,
    )
    seconds = process_time() - started

    return Encoding(
        phrases=len(table),
        dictionary=table.size,
        streams=_stream_sizes(planes, [len(stream) for stream in streams]),
        seconds=seconds,
        lossless=all(
            decode_plane(stream, table, len(plane)) == plane for plane, stream in zip(present, streams, strict=True)
        ),
        written=None,
    )


def _stream_sizes(
    planes: Sequence[bytes],
    present: Sequence[int],
) -> Tuple[int, ...]:
    """Each plane's stream size in block order, an absent plane taking none."""
    sizes = iter(present)
    return tuple(0 if is_absent(plane) else next(sizes) for plane in planes)
