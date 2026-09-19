from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.compression.planes.flags import flagged_ticks


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
        if len(self.control) != len(self.value):
            raise ValueError(
                f"a channel's control and value cover the same ticks, and these cover "
                f"{len(self.control)} and {len(self.value)}"
            )

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

    The bend plane is read on the ticks the value plane flags and on those alone: a tick left
    unflagged sounds its note's own divider. A channel that never bends therefore holds an empty
    bend plane, and one that bends holds a value only where a note does.

    Attributes:
        bend: The divider steps each flagged tick stands away from its note, held as signed bytes
            in the order the flagged ticks come.
    """

    bend: bytes

    @model_validator(mode="after")
    def _validate_the_bend_covers_the_flagged_ticks(self) -> TonePlanes:
        flagged = flagged_ticks(self.value)
        if len(self.bend) != flagged:
            raise ValueError(f"a bend plane holds a value per flagged tick, {flagged}, and this holds {len(self.bend)}")

        return self

    def bend_position(self, tick: int) -> int:
        """Where in the bend plane the song stands once ``tick`` ticks have played.

        Args:
            tick: The ticks played.

        Returns:
            int: The bend values those ticks read.
        """
        return flagged_ticks(self.value[:tick])

    @property
    def ordered(self) -> Tuple[bytes, ...]:
        """The channel's planes, in the order the song block writes them."""
        return (self.control, self.value, self.bend)
