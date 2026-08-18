from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.registers.base import ChannelRegisters
from sampletones_player.registers.hold import hold
from sampletones_player.registers.noise import NoiseRegisters
from sampletones_player.registers.pulse import PulseRegisters
from sampletones_player.registers.triangle import TriangleRegisters
from sampletones_player.specification.channels import CHANNEL_ORDER


class ChannelStreams(BaseModel):
    """The per-tick register values of all four channels, together the whole of what a song plays.

    A channel's stream ends where its instructions do, and an exporter closes a channel that was
    still sounding with one silent tick, so the four streams reach the same tick give or take that
    one. The song therefore lasts as long as its longest channel, and a channel that runs out
    first holds its final values — silent ones, every stream ending on a rest — through the ticks
    that remain.

    Attributes:
        pulse1: The first pulse channel's stream.
        pulse2: The second pulse channel's stream.
        triangle: The triangle channel's stream.
        noise: The noise channel's stream.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pulse1: Tuple[PulseRegisters, ...]
    pulse2: Tuple[PulseRegisters, ...]
    triangle: Tuple[TriangleRegisters, ...]
    noise: Tuple[NoiseRegisters, ...]

    @model_validator(mode="after")
    def _validate_every_channel_reaches_a_tick(self) -> ChannelStreams:
        empty = tuple(channel.value for channel, stream in zip(CHANNEL_ORDER, self.ordered) if not stream)
        if empty:
            raise ValueError(f"every channel needs at least one tick, and {', '.join(empty)} has none")

        return self

    @property
    def ordered(self) -> Tuple[Tuple[ChannelRegisters, ...], ...]:
        """The four streams in the order :data:`CHANNEL_ORDER` states."""
        return (self.pulse1, self.pulse2, self.triangle, self.noise)

    @property
    def ticks(self) -> int:
        """The ticks the song lasts, the longest channel stating the length."""
        return max(len(stream) for stream in self.ordered)

    @property
    def padded(self) -> Tuple[Tuple[ChannelRegisters, ...], ...]:
        """The four streams each carried to the song's full length, ready to serialise.

        Every channel reaching the same tick count is what lets the driver read a record by
        multiplying the tick by the channel's record size.
        """
        return tuple(tuple(hold(stream, tick) for tick in range(self.ticks)) for stream in self.ordered)

    def at(self, tick: int) -> Tuple[ChannelRegisters, ...]:
        """Each channel's registers at ``tick``, a channel past its end holding its final values.

        Args:
            tick: The tick to read, counted from 0.

        Returns:
            Tuple[ChannelRegisters, ...]: One register set per channel, in channel order.
        """
        return tuple(hold(stream, tick) for stream in self.ordered)
