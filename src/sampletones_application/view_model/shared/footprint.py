from typing import Dict, Optional, Self, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.footprint import (
    InstrumentFootprint,
    total_footprint,
)


class InstrumentSizeViewModel(BaseModel, frozen=True):
    """The bytes one channel's instrument occupies once a tracker compiles it.

    The measurement is carried as it was taken, both regions intact, so a display naming the
    whole and one naming a region read the same figure.
    """

    channel: ChannelName
    footprint: InstrumentFootprint

    @property
    def total_bytes(self) -> int:
        """The bytes this channel's instrument occupies, its two regions together."""
        return self.footprint.total_bytes


class SampleFootprintViewModel(BaseModel, frozen=True):
    """The byte sizes a sample's instruments occupy, one entry per channel it covers.

    A sample exports one instrument per channel its reconstruction covers, so a display reads
    :attr:`total_bytes` for the sample as a whole and :meth:`bytes_for` for a single channel.
    Both the instruments panel and the samples menu read their figures from here, so the two
    name the same size for the same sample.
    """

    instruments: Tuple[InstrumentSizeViewModel, ...]

    @classmethod
    def from_footprints(
        cls,
        footprints: Dict[ChannelName, InstrumentFootprint],
    ) -> Self:
        """Collects measured channels in the generators' own order, so displays list them alike."""
        return cls(
            instruments=tuple(
                InstrumentSizeViewModel(
                    channel=channel_name,
                    footprint=footprints[channel_name],
                )
                for channel_name in ChannelName.items()
                if channel_name in footprints
            ),
        )

    @property
    def total_bytes(self) -> int:
        """The bytes the whole sample occupies, its instruments summed region by region.

        The sum is the measurement's own, so a sample's figure and a channel's are arrived at
        the same way.
        """
        return total_footprint(instrument.footprint for instrument in self.instruments).total_bytes

    def bytes_for(self, channel: ChannelName) -> Optional[int]:
        """The bytes one channel's instrument occupies, where the sample covers that channel."""
        for instrument in self.instruments:
            if instrument.channel == channel:
                return instrument.total_bytes

        return None
