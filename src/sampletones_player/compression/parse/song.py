from typing import FrozenSet, Sequence, Tuple

from sampletones_player.compression.dictionary.table import PhraseTable
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.plane import parse_plane
from sampletones_player.compression.parse.result import Parse


def parse_planes(
    indices: Sequence[PlaneIndex],
    table: PhraseTable,
    options: CodecOptions,
    boundaries: FrozenSet[int],
) -> Tuple[Parse, ...]:
    """Reads every plane of a song against one dictionary.

    Args:
        indices: The planes and the readings of them matching is decided against.
        table: The phrases the planes may play.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on.

    Returns:
        Tuple[Parse, ...]: One parse per plane, in the order the planes were given.
    """
    matcher = PhraseMatcher(table)
    return tuple(parse_plane(index, matcher, options, boundaries) for index in indices)
