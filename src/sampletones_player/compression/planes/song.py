from __future__ import annotations

from typing import Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_player.compression.planes.channel import ChannelPlanes
from sampletones_player.compression.planes.order import PlaneOrder


class SongPlanes(BaseModel):
    """Every channel of a song separated into planes, the whole of what the codec compresses.

    Attributes:
        pulse1: The first pulse channel's planes.
        pulse2: The second pulse channel's planes.
        triangle: The triangle channel's planes.
        noise: The noise channel's planes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pulse1: ChannelPlanes
    pulse2: ChannelPlanes
    triangle: ChannelPlanes
    noise: ChannelPlanes

    @classmethod
    def from_order(cls, planes: PlaneOrder) -> SongPlanes:
        """Gathers eight planes back into the four channels that write them.

        Args:
            planes: The eight planes, in the order the song block writes them.

        Returns:
            SongPlanes: The planes under the channel each pair belongs to.
        """
        return cls(
            pulse1=ChannelPlanes(
                control=planes.pulse1_control,
                value=planes.pulse1_value,
            ),
            pulse2=ChannelPlanes(
                control=planes.pulse2_control,
                value=planes.pulse2_value,
            ),
            triangle=ChannelPlanes(
                control=planes.triangle_control,
                value=planes.triangle_value,
            ),
            noise=ChannelPlanes(
                control=planes.noise_control,
                value=planes.noise_value,
            ),
        )

    @model_validator(mode="after")
    def _validate_every_channel_reaches_the_same_tick(self) -> SongPlanes:
        lengths = {channels.ticks for channels in self.ordered}
        if len(lengths) > 1:
            raise ValueError(f"a song's channels cover the same ticks, and these cover {sorted(lengths)}")

        return self

    @property
    def ordered(self) -> Tuple[ChannelPlanes, ...]:
        """The four channels in the order the generator names run."""
        return (self.pulse1, self.pulse2, self.triangle, self.noise)

    @property
    def planes(self) -> PlaneOrder:
        """The eight planes in the order the song block writes them."""
        return PlaneOrder(
            pulse1_control=self.pulse1.control,
            pulse1_value=self.pulse1.value,
            pulse2_control=self.pulse2.control,
            pulse2_value=self.pulse2.value,
            triangle_control=self.triangle.control,
            triangle_value=self.triangle.value,
            noise_control=self.noise.control,
            noise_value=self.noise.value,
        )

    @property
    def ticks(self) -> int:
        """The ticks the song lasts."""
        return self.pulse1.ticks
