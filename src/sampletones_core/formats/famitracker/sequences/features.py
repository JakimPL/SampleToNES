from typing import Dict

from sampletones_core.exporters.feature import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    FEATURE_KEY_TO_SEQUENCE_KIND,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)


def features_to_instrument_sequences(features: Features) -> Dict[SequenceKind, InstrumentSequence]:
    """Builds the five 2A03 sequences from a channel slice's envelopes.

    Each dimension becomes an :class:`InstrumentSequence`; one the generator lacks, or one left
    to the channel, becomes a disabled sequence the instrument stores nothing for. Item counts
    stay within the ``MAX_SEQUENCE_ITEMS`` items FamiTracker holds, so a longer reconstruction
    exports its opening frames and the shortening is logged. Every dimension keeps the length it
    was written at and the item it repeats from, which is how FamiTracker advances each sequence
    on a counter of its own.

    Args:
        features: The per-dimension envelopes describing the slice.

    Returns:
        Dict[SequenceKind, InstrumentSequence]: The sequences, one per dimension FamiTracker holds.
    """
    written = {
        FEATURE_KEY_TO_SEQUENCE_KIND[feature_key]: envelope.limited(MAX_SEQUENCE_ITEMS)
        for feature_key, envelope in features.envelopes.items()
    }

    return {kind: _sequence(kind, written.get(kind, Envelope[int]())) for kind in SequenceKind}


def _sequence(kind: SequenceKind, envelope: Envelope[int]) -> InstrumentSequence:
    """One sequence as the file states it, with the item the dimension repeats from."""
    return InstrumentSequence(
        kind=kind,
        items=envelope.items,
        loop_point=envelope.loop_point if envelope.loop_point is not None else NO_LOOP_POINT,
    )
