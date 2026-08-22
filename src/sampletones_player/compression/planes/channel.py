from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, model_validator


class ChannelPlanes(BaseModel):
    """One channel's ticks separated into the two byte series it writes.

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
    def _validate_both_planes_cover_the_same_ticks(self) -> ChannelPlanes:
        if len(self.control) != len(self.value):
            raise ValueError(
                f"a channel's planes cover the same ticks, and these cover "
                f"{len(self.control)} and {len(self.value)}"
            )

        if not self.control:
            raise ValueError("a channel's planes cover at least one tick")

        return self

    @property
    def ticks(self) -> int:
        """The ticks both planes cover."""
        return len(self.control)

    @property
    def ordered(self) -> Tuple[bytes, ...]:
        """Both planes, in the order the song block writes them."""
        return (self.control, self.value)
