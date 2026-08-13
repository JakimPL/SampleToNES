from typing import Dict, Optional, Tuple

import numpy as np

from sampletones_core.exporters.lengths import equalize_lengths, limit_lengths
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import (
    LOOP_FROM_START,
    MAX_SEQUENCE_ITEMS,
    NO_LOOP_POINT,
    SequenceKind,
)


def _to_items(array: Optional[np.ndarray]) -> Tuple[int, ...]:
    if array is None:
        return ()
    return tuple(int(value) for value in array)


def _sequence_items(
    arrays: Dict[SequenceKind, Optional[np.ndarray]],
    loop: bool,
) -> Dict[SequenceKind, Tuple[int, ...]]:
    """Reads the dimensions as the item tuples an instrument stores.

    A looping instrument brings every populated dimension to one length, so its envelopes
    repeat in step cycle after cycle. A one-shot carries each dimension at the length it
    was written: a FamiTracker sequence that runs out halts and leaves its final value
    applied for as long as the note sounds, so the shorter dimensions govern the whole
    instrument on their own.
    """
    items_by_kind = {kind: _to_items(array) for kind, array in arrays.items()}
    if loop:
        return equalize_lengths(items_by_kind, loop, limit=MAX_SEQUENCE_ITEMS)

    return limit_lengths(items_by_kind, limit=MAX_SEQUENCE_ITEMS)


def features_to_instrument_sequences(
    *,
    volume: np.ndarray,
    arpeggio: np.ndarray,
    pitch: Optional[np.ndarray],
    hi_pitch: Optional[np.ndarray],
    duty_cycle: Optional[np.ndarray],
    loop: bool,
) -> Dict[SequenceKind, InstrumentSequence]:
    """Builds the five 2A03 sequences from per-dimension envelope arrays.

    Each dimension becomes an :class:`InstrumentSequence`; a dimension passed as ``None``
    or as an empty envelope becomes a disabled sequence the instrument stores nothing for.
    Item counts stay within the ``MAX_SEQUENCE_ITEMS`` items FamiTracker holds, so a longer
    reconstruction exports its opening frames and the shortening is logged. When ``loop``
    is set, every populated sequence loops from its first item so the instrument sustains
    on a held note, and the populated dimensions share one length to repeat in step.
    """
    arrays: Dict[SequenceKind, Optional[np.ndarray]] = {
        SequenceKind.VOLUME: volume,
        SequenceKind.ARPEGGIO: arpeggio,
        SequenceKind.PITCH: pitch,
        SequenceKind.HI_PITCH: hi_pitch,
        SequenceKind.DUTY: duty_cycle,
    }

    items_by_kind = _sequence_items(arrays, loop)

    sequences: Dict[SequenceKind, InstrumentSequence] = {}
    for kind, items in items_by_kind.items():
        loop_point = LOOP_FROM_START if loop and items else NO_LOOP_POINT
        sequences[kind] = InstrumentSequence(
            kind=kind,
            items=items,
            loop_point=loop_point,
        )

    return sequences
