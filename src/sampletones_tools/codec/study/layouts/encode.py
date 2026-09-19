from time import process_time

from sampletones_player.compression.decode import decode_plane
from sampletones_player.compression.encode import encode_streams
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.layouts.layout import PlaneLayout
from sampletones_tools.codec.study.layouts.planes import layout_planes, layout_seeds
from sampletones_tools.codec.study.measure import Encoding
from sampletones_tools.codec.study.variants.production import NO_LOOP_BOUNDARIES


def encode_layout(
    song: StudySong,
    layout: PlaneLayout,
) -> Encoding:
    """Encodes a song's planes written under a layout, every layer of the production codec on.

    Args:
        song: The song to encode.
        layout: How each tone channel's divider is written.

    Returns:
        Encoding: The encoding, an absent plane's stream counted as nothing.
    """
    planes = layout_planes(song, layout)
    seeds = layout_seeds(song.slices, song.pitches, layout)

    started = process_time()
    table, streams = encode_streams(
        planes,
        seeds,
        options=EVERY_LAYER,
        boundaries=(NO_LOOP_BOUNDARIES,) * len(planes),
    )
    seconds = process_time() - started

    return Encoding(
        phrases=len(table),
        dictionary=table.size,
        streams=tuple(len(stream) for stream in streams),
        seconds=seconds,
        lossless=all(
            decode_plane(stream, table, len(plane)) == plane for plane, stream in zip(planes, streams, strict=True)
        ),
        written=None,
    )
