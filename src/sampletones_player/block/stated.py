from __future__ import annotations

from typing import NamedTuple

from sampletones_core.formats.binary import BinaryReader
from sampletones_player.specification.clock import FIXED_POINT_BITS


class StatedSong(NamedTuple):
    """What a song block's header states about the playing: the clock, the length and the loop.

    Attributes:
        step: The ticks the driver advances on each play call, in ``1 / FIXED_POINT_SCALE`` ticks.
        ticks: The ticks the song lasts.
        loop_tick: The tick the song repeats from, or ``NO_LOOP``.
    """

    step: int
    ticks: int
    loop_tick: int

    @classmethod
    def read(cls, block: bytes) -> StatedSong:
        """Reads the fields leading a song block, in the order the block writes them.

        Raises:
            TruncatedDataError: If the block ends before its header does.
        """
        reader = BinaryReader(block)
        whole = reader.read_uint8()
        fraction = reader.read_uint16()
        ticks = reader.read_uint16()
        loop_tick = reader.read_uint16()
        return cls(step=(whole << FIXED_POINT_BITS) | fraction, ticks=ticks, loop_tick=loop_tick)
