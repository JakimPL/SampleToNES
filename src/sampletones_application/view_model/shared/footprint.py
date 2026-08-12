from typing import Dict, Optional, Self, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.formats.famitracker.footprint import InstrumentFootprint


class InstrumentSizeViewModel(BaseModel, frozen=True):
    """The bytes one channel's instrument occupies once a tracker compiles it."""

    generator: GeneratorName
    total_bytes: int


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
        footprints: Dict[GeneratorName, InstrumentFootprint],
    ) -> Self:
        """Collects measured channels in the generators' own order, so displays list them alike."""
        return cls(
            instruments=tuple(
                InstrumentSizeViewModel(
                    generator=generator_name,
                    total_bytes=footprints[generator_name].total_bytes,
                )
                for generator_name in GeneratorName.items()
                if generator_name in footprints
            ),
        )

    @property
    def total_bytes(self) -> int:
        """The bytes the whole sample occupies, its instruments summed."""
        return sum(instrument.total_bytes for instrument in self.instruments)

    def bytes_for(self, generator: GeneratorName) -> Optional[int]:
        """The bytes one channel's instrument occupies, where the sample covers that channel."""
        for instrument in self.instruments:
            if instrument.generator == generator:
                return instrument.total_bytes

        return None
