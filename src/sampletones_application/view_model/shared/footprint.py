from typing import Dict, Optional, Self, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.footprint import (
    InstrumentFootprint,
    total_footprint,
)


class InstrumentSizeViewModel(BaseModel, frozen=True):
    """The bytes one instrument occupies once a tracker compiles it.

    The measurement is carried as it was taken, both regions intact, so a display naming the
    whole and one naming a region read the same figure. An instrument naming a channel is a
    sample's slice of that channel; one naming none is a shape, stored once for every channel
    that reaches it.
    """

    channel: Optional[ChannelName]
    footprint: InstrumentFootprint

    @property
    def total_bytes(self) -> int:
        """The bytes this instrument occupies, its two regions together."""
        return self.footprint.total_bytes


class SampleFootprintViewModel(BaseModel, frozen=True):
    """The byte sizes a voice's instruments occupy.

    A sample exports one instrument per channel its reconstruction covers, so a display reads
    :attr:`total_bytes` for the voice as a whole and :meth:`bytes_for` for a single channel. A
    shape exports one instrument every channel reaches, so it carries a single entry and its
    whole figure is that instrument's. Both the instruments panel and the voices menu read their
    figures from here, so the two name the same size for the same voice.
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

    @classmethod
    def from_instrument(cls, footprint: InstrumentFootprint) -> Self:
        """Carries one instrument every channel reaches, which is what a shape exports."""
        return cls(instruments=(InstrumentSizeViewModel(channel=None, footprint=footprint),))

    @property
    def total_bytes(self) -> int:
        """The bytes the whole voice occupies, its instruments summed region by region.

        The sum is the measurement's own, so a voice's figure and a channel's are arrived at
        the same way.
        """
        return total_footprint(instrument.footprint for instrument in self.instruments).total_bytes

    def bytes_for(self, channel: ChannelName) -> Optional[int]:
        """The bytes one channel's instrument occupies, where the sample covers that channel."""
        for instrument in self.instruments:
            if instrument.channel == channel:
                return instrument.total_bytes

        return None
