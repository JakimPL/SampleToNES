from dataclasses import dataclass
from typing import Dict, Iterable

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.feature import Features
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.sequences.features import (
    features_to_instrument_sequences,
)
from sampletones_core.formats.famitracker.specification.memory import (
    INSTRUMENT_DEFINITION_BYTES,
    SEQUENCE_HEADER_BYTES,
    SEQUENCE_ITEM_BYTES,
    SEQUENCE_POINTER_BYTES,
)
from sampletones_core.reconstructions import Reconstruction


@dataclass(frozen=True)
class InstrumentFootprint:
    """The bytes an instrument occupies once FamiTracker compiles it into an NSF.

    The two fields are the two regions the driver keeps an instrument in, which FamiTracker's
    own export log reports side by side: the instrument list and body under ``instrument_bytes``,
    the sequence chunks the body points at under ``sequence_bytes``. See
    `docs/formats/famitracker.md` for the layout each figure counts.

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


def sequence_footprint(sequence: InstrumentSequence) -> int:
    """Measures the bytes one sequence chunk occupies: its four-field header and its items."""
    return SEQUENCE_HEADER_BYTES + SEQUENCE_ITEM_BYTES * len(sequence.items)


def sequences_footprint(
    sequences: Iterable[InstrumentSequence],
) -> InstrumentFootprint:
    """Measures the instrument the given sequences make up.

    A populated sequence earns the instrument a pointer to its chunk and contributes the chunk
    itself; an empty one is written as a disabled slot the driver stores nothing for, so the
    populated sequences alone decide both figures.
    """
    populated = [sequence for sequence in sequences if sequence.enabled]
    return InstrumentFootprint(
        instrument_bytes=INSTRUMENT_DEFINITION_BYTES + SEQUENCE_POINTER_BYTES * len(populated),
        sequence_bytes=sum(sequence_footprint(sequence) for sequence in populated),
    )


def instrument_footprint(instrument: Instrument2A03) -> InstrumentFootprint:
    """Measures one built instrument, the form an export writes."""
    return sequences_footprint(instrument.sequences.values())


def features_footprint(
    features: Features,
    *,
    loop: bool,
) -> InstrumentFootprint:
    """Measures the instrument a generator slice's envelopes export to.

    The envelopes pass through the same builder an export uses, so the measured item counts are
    the ones a file carries: brought to one shared length and capped at what a FamiTracker
    sequence holds.

    Args:
        features: The per-dimension envelopes describing the slice.
        loop: Whether the instrument loops while its note is held, which decides the shared length.

    Returns:
        InstrumentFootprint: The footprint of the instrument those envelopes describe.
    """
    sequences = features_to_instrument_sequences(
        volume=features.volume,
        arpeggio=features.arpeggio,
        pitch=features.pitch,
        hi_pitch=features.hi_pitch,
        duty_cycle=features.duty_cycle,
        loop=loop,
    )
    return sequences_footprint(sequences.values())


def reconstruction_footprints(
    reconstruction: Reconstruction,
    *,
    loop: bool,
) -> Dict[GeneratorName, InstrumentFootprint]:
    """Measures one instrument per channel a reconstruction covers.

    A reconstruction exports one instrument for each of its one to four channels, so the result
    holds an entry per covered channel and :func:`total_footprint` sums them into what the whole
    sample costs.

    Args:
        reconstruction: The reconstruction whose channels are measured.
        loop: Whether the sample carrying it loops while its note is held.

    Returns:
        Dict[GeneratorName, InstrumentFootprint]: The footprint of each channel's instrument.
    """
    return {
        generator_name: features_footprint(features, loop=loop)
        for generator_name, features in reconstruction.export().items()
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
