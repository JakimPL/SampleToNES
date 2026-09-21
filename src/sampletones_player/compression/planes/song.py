from __future__ import annotations

from typing import Final, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from sampletones_core.constants.enums import ChannelName
from sampletones_player.compression.planes.flags import flagged_ticks
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.planes import (
    PLANES,
    PlaneRole,
    channel_indices,
    plane_index,
)

FIRST_PLANE: Final[int] = 0


class SongPlanes(BaseModel):
    """Every plane of a song, in the order the song block writes them.

    A channel writes what it sounds and how it sounds it as separate byte series. Read tick by
    tick those braid together, and each turns over at its own pace — a volume envelope decays
    while a pitch holds, a pitch walks while the timbre stays put. Kept apart, each is a series
    that repeats and rests on its own terms, which is the form the codec reads them in.

    A bend plane holds a value on the ticks its channel's value plane flags and on those alone,
    so it covers fewer ticks than the song lasts while every other plane covers them all.

    Attributes:
        planes: The byte series each plane plays, under the name the song block writes it by.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    planes: PlaneOrder

    @model_validator(mode="after")
    def _validate_every_plane_covers_the_song(self) -> SongPlanes:
        if not self.planes[FIRST_PLANE]:
            raise ValueError("a song's planes cover at least one tick")

        for plane, played in zip(PLANES, self.planes, strict=True):
            reach = self._flagged(plane.channel) if plane.spans_flagged_ticks else self.ticks
            if len(played) != reach:
                raise ValueError(
                    f"the {plane.name} plane covers {reach} of the song's values, and this covers {len(played)}"
                )

        return self

    def _flagged(self, channel: ChannelName) -> int:
        return flagged_ticks(self.planes[plane_index(channel, PlaneRole.VALUE)])

    @property
    def ticks(self) -> int:
        """The ticks the song lasts."""
        return len(self.planes[FIRST_PLANE])

    def of(self, channel: ChannelName) -> Tuple[bytes, ...]:
        """The planes ``channel`` writes, in the order the song block writes them.

        Args:
            channel: The channel to read.

        Returns:
            Tuple[bytes, ...]: That channel's own planes.
        """
        return tuple(self.planes[index] for index in channel_indices(channel))

    def positions(self, tick: int) -> Tuple[int, ...]:
        """Where each plane stands once ``tick`` ticks have played, in block order.

        Every plane reads one value a tick but a bend plane, which reads one on each tick its
        channel flags, so a song returning to a tick re-enters each plane at a position of its own.

        Args:
            tick: The ticks played.

        Returns:
            Tuple[int, ...]: One position per plane.
        """
        return tuple(
            (
                flagged_ticks(self.planes[plane_index(plane.channel, PlaneRole.VALUE)][:tick])
                if plane.spans_flagged_ticks
                else tick
            )
            for plane in PLANES
        )
