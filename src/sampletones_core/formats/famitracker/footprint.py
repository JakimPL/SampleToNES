from dataclasses import dataclass
from typing import Dict, Iterable

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.specification.memory import (
    INSTRUMENT_DEFINITION_BYTES,
    SEQUENCE_HEADER_BYTES,
    SEQUENCE_ITEM_BYTES,
    SEQUENCE_POINTER_BYTES,
)
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class InstrumentFootprint:
    """The raw bytes an instrument's envelopes take, laid out the way FamiTracker's driver lays them out.

    The two fields are the two regions the driver keeps an instrument in, which FamiTracker's
    own export log reports side by side: the instrument list and body under ``instrument_bytes``,
    the sequence chunks the body points at under ``sequence_bytes``. Every item an envelope
    carries is counted, so the figure is the size of the sound's data before any compression.
    See `docs/formats/famitracker.md` for the layout each figure counts.

    Attributes:
        instrument_bytes: Bytes the instrument's table entry and body occupy.
        sequence_bytes: Bytes the instrument's sequences occupy.
    """

    instrument_bytes: int
    sequence_bytes: int

    @property
    def total_bytes(self) -> int:
        """The whole footprint, the figure a size display names."""
        return self.instrument_bytes + self.sequence_bytes


def envelope_footprint(envelope: Envelope[int]) -> int:
    """Measures the bytes one envelope occupies as a sequence chunk: its four-field header and its items."""
    return SEQUENCE_HEADER_BYTES + SEQUENCE_ITEM_BYTES * len(envelope.items)


def features_footprint(features: Features) -> InstrumentFootprint:
    """Measures the instrument a channel slice's envelopes make up, every item they carry counted.

    A written envelope earns the instrument a pointer to its chunk and contributes the chunk at
    its whole length; a dimension left to the channel is a disabled slot the driver stores
    nothing for. The figure describes the envelopes as the application plays them, and an export
    to FamiTracker shapes them to its own sequences (see `docs/formats/famitracker.md`).

    Args:
        features: The per-dimension envelopes describing the slice.

    Returns:
        InstrumentFootprint: The footprint of the instrument those envelopes describe.
    """
    written = [envelope for envelope in features.envelopes.values() if envelope.written]
    return InstrumentFootprint(
        instrument_bytes=INSTRUMENT_DEFINITION_BYTES + SEQUENCE_POINTER_BYTES * len(written),
        sequence_bytes=sum(envelope_footprint(envelope) for envelope in written),
    )


def reconstruction_footprints(reconstruction: Reconstruction) -> Dict[ChannelName, InstrumentFootprint]:
    """Measures one instrument per channel a reconstruction plays.

    An export writes an instrument for each channel that plays, so the result holds an entry
    per playing channel and :func:`total_footprint` sums them into what the whole sample costs.
    A channel standing by is written nowhere and therefore measured nowhere.

    Args:
        reconstruction: The reconstruction whose channels are measured.

    Returns:
        Dict[ChannelName, InstrumentFootprint]: The footprint of each playing channel's instrument.
    """
    return {
        channel_name: features_footprint(features)
        for channel_name, features in reconstruction.export().items()
        if features.has_frames
    }


def total_footprint(
    footprints: Iterable[InstrumentFootprint],
) -> InstrumentFootprint:
    """Sums footprints region by region, giving what a set of instruments costs together."""
    measured = list(footprints)
    return InstrumentFootprint(
        instrument_bytes=sum(footprint.instrument_bytes for footprint in measured),
        sequence_bytes=sum(footprint.sequence_bytes for footprint in measured),
    )
