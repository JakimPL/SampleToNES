from functools import cached_property
from typing import AbstractSet, Any, Dict, FrozenSet, List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.algorithm import (
    ALL_STEMS_CHANNEL_CAP,
    MAX_DRIVE,
    MIN_DRIVE,
    MIN_STEMS_CHANNEL_CAP,
    UNIT_DRIVE,
)
from sampletones_core.constants.enums import (
    TONE_CHANNELS,
    ChannelName,
    bending_channels,
    ordered_channels,
)
from sampletones_core.data import DataModel

CHANNELS_FIELD: str = "channels"
DRIVES_FIELD: str = "drives"


class StemSettings(DataModel):
    """What one recording is converted with: the channels it may occupy, which of them it bends,
    how hard it pushes each of them, and how many of them it sounds at once.

    A recording's settings are one value, so the list a reader sets a run up in, the entry that run
    records, and whoever reads the record later all state the same thing. A further per-recording
    choice is a field here, and each of those readers gains it in the same step.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    channels: List[ChannelName] = Field(
        ...,
        description="The channels the recording may occupy",
    )
    bends: List[ChannelName] = Field(
        ...,
        description="The channels whose notes the recording carries to the divider it sounds",
    )
    drives: Dict[ChannelName, float] = Field(
        default_factory=dict,
        description="How hard the recording pushes each channel it may occupy",
    )
    channel_cap: int = Field(
        default=ALL_STEMS_CHANNEL_CAP,
        ge=MIN_STEMS_CHANNEL_CAP,
        le=ALL_STEMS_CHANNEL_CAP,
        description="The most channels the recording sounds in one frame",
    )

    @classmethod
    def covering(cls, channels: List[ChannelName]) -> Self:
        """The usual settings over ``channels``: every tone channel bent, unit drive, every channel at once.

        This is what a recording is converted with until a reader says otherwise, and the shape a
        single-file conversion runs under.
        """
        return cls(
            channels=channels,
            bends=bending_channels(channels),
            drives={channel_name: UNIT_DRIVE for channel_name in channels},
            channel_cap=ALL_STEMS_CHANNEL_CAP,
        )

    @cached_property
    def channel_set(self) -> FrozenSet[ChannelName]:
        """The channels the recording may occupy, in the form an assignment tests membership against."""
        return frozenset(self.channels)

    @cached_property
    def bend_set(self) -> FrozenSet[ChannelName]:
        """The channels the recording bends, in the form the refinement tests membership against."""
        return frozenset(self.bends)

    def with_channels(self, channels: AbstractSet[ChannelName]) -> Self:
        """The settings occupying exactly ``channels``, keeping what still reaches one of them.

        A bend and a drive belong to a channel the recording occupies, so narrowing the channels
        narrows both along with them, and a channel newly occupied plays at unit drive. The count
        stays the reader's choice.
        """
        held = ordered_channels(channels)
        return self.__class__(
            channels=held,
            bends=ordered_channels(self.bend_set & frozenset(held)),
            drives={channel_name: self.drives.get(channel_name, UNIT_DRIVE) for channel_name in held},
            channel_cap=self.channel_cap,
        )

    def with_bends(self, bends: AbstractSet[ChannelName]) -> Self:
        """The settings bending ``bends``, each held to an occupied channel whose hardware reads one."""
        reached = frozenset(bends) & self.channel_set & TONE_CHANNELS
        return self.__class__(
            channels=self.channels,
            bends=ordered_channels(reached),
            drives=self.drives,
            channel_cap=self.channel_cap,
        )

    def with_drive(self, channel_name: ChannelName, drive: float) -> Self:
        """The settings pushing ``channel_name`` with ``drive``.

        Raises:
            ValueError: If the recording leaves ``channel_name`` unoccupied, or ``drive`` lies
                outside the bounds a drive has.
        """
        if channel_name not in self.channel_set:
            raise ValueError(f"The recording leaves {channel_name} unoccupied, so it carries no drive there")

        return self.__class__(
            channels=self.channels,
            bends=self.bends,
            drives={**self.drives, channel_name: drive},
            channel_cap=self.channel_cap,
        )

    def with_channel_cap(self, channel_cap: int) -> Self:
        """The settings sounding at most ``channel_cap`` channels in one frame."""
        return self.__class__(
            channels=self.channels,
            bends=self.bends,
            drives=self.drives,
            channel_cap=channel_cap,
        )

    @model_validator(mode="before")
    @classmethod
    def _every_channel_holds_a_drive(cls, data: Any) -> Any:
        """Gives a channel stated without a drive the unit drive.

        A setup states a drive for the channels it pushes away from unit, and the rest play as
        calibrated, so a stems file, a settings file and a record written before drives existed
        each read as complete settings.
        """
        if not isinstance(data, dict):
            return data

        channels = data.get(CHANNELS_FIELD)
        if not isinstance(channels, list):
            return data

        drives = dict(data.get(DRIVES_FIELD) or {})
        for channel_name in channels:
            drives.setdefault(channel_name, UNIT_DRIVE)

        return {**data, DRIVES_FIELD: drives}

    @model_validator(mode="after")
    def _bends_reach_their_channels(self) -> Self:
        """Holds a bend to a channel the recording occupies and whose hardware loads a divider.

        Raises:
            ValueError: If a bent channel lies outside the recording's own channels, or names the
                noise channel, whose sixteen periods stand at fixed distances from each other.
        """
        unheld = self.bend_set - self.channel_set
        if unheld:
            raise ValueError(f"Bent channels lie outside the ones occupied: {sorted(unheld)}")

        toneless = self.bend_set - TONE_CHANNELS
        if toneless:
            raise ValueError(f"Bent channels read no bend: {sorted(toneless)}")

        return self

    @model_validator(mode="after")
    def _drives_name_the_channels(self) -> Self:
        """Holds a drive to each channel the recording occupies and to the bounds a drive has.

        Raises:
            ValueError: If the drives name a channel outside the ones occupied, or a drive lies
                below ``MIN_DRIVE`` or above ``MAX_DRIVE``.
        """
        named = frozenset(self.drives)
        if named != self.channel_set:
            raise ValueError(f"Drives name {sorted(named)} where the recording occupies {sorted(self.channel_set)}")

        for channel_name, drive in self.drives.items():
            if not MIN_DRIVE <= drive <= MAX_DRIVE:
                raise ValueError(f"The drive on {channel_name} lies outside [{MIN_DRIVE}, {MAX_DRIVE}]: {drive}")

        return self
