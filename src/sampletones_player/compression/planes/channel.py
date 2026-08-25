from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, model_validator


class ChannelPlanes(BaseModel):
    """One channel's ticks separated into the byte series it writes.

    A channel writes two things each tick: how it sounds and what it sounds. Read tick by tick
    those two braid together, and each turns over at its own pace — a volume envelope decays
    while a pitch holds, a pitch walks while the timbre stays put. Kept apart, each is a series
    that repeats and rests on its own terms, which is the form the codec reads them in.

    Attributes:
        control: The timbre byte each tick writes, volume riding in it where a channel has one.
        value: The pitch each tick sounds, as an index into the pitch table, or the noise
            channel's period byte.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    control: bytes
    value: bytes

    @model_validator(mode="after")
    def _validate_every_plane_covers_the_same_ticks(self) -> ChannelPlanes:
        lengths = {len(plane) for plane in self.ordered}
        if len(lengths) > 1:
            raise ValueError(f"a channel's planes cover the same ticks, and these cover {sorted(lengths)}")

        if not self.control:
            raise ValueError("a channel's planes cover at least one tick")

        return self

    @property
    def ticks(self) -> int:
        """The ticks the channel's planes cover."""
        return len(self.control)

    @property
    def ordered(self) -> Tuple[bytes, ...]:
        """The channel's planes, in the order the song block writes them."""
        return (self.control, self.value)


class TonePlanes(ChannelPlanes):
    """A tone channel's ticks, the divider each one sounds at named in two parts.

    A tone channel reaches its divider through the pitch table, and a frame may stand away from
    the note it names. The value plane holds the note, which is what lets a phrase be transposed
    by adding to it, and the bend plane holds how far the frame stands from it — so the divider
    the hardware takes is the sum, and each half repeats on its own terms.

    Attributes:
        bend: The divider steps each tick stands away from its note, held as a signed byte.
    """

    bend: bytes

    @property
    def ordered(self) -> Tuple[bytes, ...]:
        """The channel's planes, in the order the song block writes them."""
        return (self.control, self.value, self.bend)
