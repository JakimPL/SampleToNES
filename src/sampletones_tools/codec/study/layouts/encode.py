from time import process_time

from sampletones_player.compression.decode import decode_plane
from sampletones_player.compression.encode import encode_streams
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.planes.symbols import pack_plane
from sampletones_player.specification.planes import PLANES
from sampletones_player.specification.song import SONG_HEADER_SIZE
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
    packed = tuple(
        b"" if plane.idles(played) else pack_plane(played, plane.form, boundaries=NO_LOOP_BOUNDARIES)
        for plane, played in zip(PLANES, planes, strict=True)
    )

    started = process_time()
    table, streams = encode_streams(
        packed,
        seeds,
        options=EVERY_LAYER,
        boundaries=(NO_LOOP_BOUNDARIES,) * len(packed),
    )
    seconds = process_time() - started

    return Encoding(
        header=SONG_HEADER_SIZE,
        phrases=len(table),
        dictionary=table.size,
        streams=tuple(len(stream) for stream in streams),
        seconds=seconds,
        lossless=all(
            decode_plane(stream, table, plane, len(played)) == played
            for plane, played, stream in zip(PLANES, planes, streams, strict=True)
        ),
        written=None,
    )
