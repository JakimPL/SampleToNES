from typing import FrozenSet, Optional, Sequence

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.decode import decode_planes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.encode import encode_planes
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.rebuild import streams_from_planes
from sampletones_player.compression.planes.separate import planes_from_streams
from sampletones_player.registers.streams import ChannelStreams


def _entries(loop_tick: Optional[int]) -> FrozenSet[int]:
    if loop_tick is None:
        return frozenset()

    return frozenset({loop_tick})


def compress_song(
    streams: ChannelStreams,
    pitches: PitchTable,
    *,
    seeds: Sequence[Phrase],
    loop_tick: Optional[int] = None,
) -> CompressedPlanes:
    """Compresses a song's four register streams into the dictionary and streams a file carries.

    A song that repeats re-enters its streams partway through, so the tick it returns to holds a
    token of its own on every plane: what the driver needs to resume there is a source pointer,
    and a token that leans on the value a plane already reached would need the run that led to it.

    Args:
        streams: The per-tick register values every channel plays.
        pitches: The timer each pitch sounds at, which is what turns a timer into an index.
        seeds: The phrases the song's instruments offer the dictionary.
        loop_tick: The tick the song returns to once it ends, or ``None`` where it stops there.

    Returns:
        CompressedPlanes: The dictionary, the eight token streams and the ticks the song lasts.

    Raises:
        ValueError: If a stream sounds a timer the pitch table states no index for.
    """
    return encode_planes(
        planes_from_streams(streams, pitches),
        seeds,
        options=EVERY_LAYER,
        boundaries=_entries(loop_tick),
    )


def decompress_song(
    planes: CompressedPlanes,
    pitches: PitchTable,
) -> ChannelStreams:
    """Plays a song's token streams back into the register values every channel writes.

    This is the reading the driver performs, stated where it is testable: the trace the assembly
    is held against is taken from it, so what the console plays and what the file holds are the
    same values.

    Args:
        planes: The dictionary, the eight token streams and the ticks the song lasts.
        pitches: The timer each pitch sounds at, which is what turns an index back into a timer.

    Returns:
        ChannelStreams: The per-tick register values every channel plays.
    """
    return streams_from_planes(decode_planes(planes), pitches)
