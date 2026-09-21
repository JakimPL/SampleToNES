from __future__ import annotations

from enum import StrEnum
from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName


class PlaneRole(StrEnum):
    """The part of a channel's tick one plane carries.

    Attributes:
        CONTROL: How the channel sounds — its timbre, and its volume where it has one.
        VALUE: What the channel sounds — a pitch index, or the noise channel's period byte.
        BEND: How far a tick stands from the divider the pitch it names sounds at.
    """

    CONTROL = "control"
    VALUE = "value"
    BEND = "bend"


class Plane(BaseModel):
    """One byte series a song block writes, named by the channel and the part it carries.

    Attributes:
        channel: The channel the plane belongs to.
        role: The part of the channel's tick the plane carries.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channel: ChannelName
    role: PlaneRole

    @property
    def name(self) -> str:
        """The name the song block writes the plane under."""
        return f"{self.channel.value}_{self.role.value}"

    @property
    def spans_flagged_ticks(self) -> bool:
        """Whether the plane holds a value per flagged tick rather than one per tick."""
        return self.role is PlaneRole.BEND


PLANES: Final[Tuple[Plane, ...]] = (
    Plane(channel=ChannelName.PULSE1, role=PlaneRole.CONTROL),
    Plane(channel=ChannelName.PULSE1, role=PlaneRole.VALUE),
    Plane(channel=ChannelName.PULSE1, role=PlaneRole.BEND),
    Plane(channel=ChannelName.PULSE2, role=PlaneRole.CONTROL),
    Plane(channel=ChannelName.PULSE2, role=PlaneRole.VALUE),
    Plane(channel=ChannelName.PULSE2, role=PlaneRole.BEND),
    Plane(channel=ChannelName.TRIANGLE, role=PlaneRole.CONTROL),
    Plane(channel=ChannelName.TRIANGLE, role=PlaneRole.VALUE),
    Plane(channel=ChannelName.TRIANGLE, role=PlaneRole.BEND),
    Plane(channel=ChannelName.NOISE, role=PlaneRole.CONTROL),
    Plane(channel=ChannelName.NOISE, role=PlaneRole.VALUE),
)
PLANE_COUNT: Final[int] = len(PLANES)
PLANE_NAMES: Final[Tuple[str, ...]] = tuple(plane.name for plane in PLANES)


def channel_indices(channel: ChannelName) -> Tuple[int, ...]:
    """Where ``channel``'s own planes stand in the song block, in the order it writes them.

    Args:
        channel: The channel to read.

    Returns:
        Tuple[int, ...]: The positions that channel's planes take.
    """
    return tuple(index for index, plane in enumerate(PLANES) if plane.channel is channel)


def plane_index(
    channel: ChannelName,
    role: PlaneRole,
) -> int:
    """Where the plane ``channel`` writes for ``role`` stands in the song block.

    Args:
        channel: The channel the plane belongs to.
        role: The part of the channel's tick the plane carries.

    Returns:
        int: The position the plane takes.

    Raises:
        ValueError: If the channel writes no plane for that role.
    """
    for index, plane in enumerate(PLANES):
        if plane.channel is channel and plane.role is role:
            return index

    raise ValueError(f"the {channel.value} channel writes no {role.value} plane")
