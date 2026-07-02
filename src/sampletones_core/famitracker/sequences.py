from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from sampletones_core.famitracker.model.sequence import InstrumentSequence
from sampletones_core.famitracker.specification.sequences import (
    LOOP_FROM_START,
    NO_LOOP_POINT,
    SequenceKind,
)


def _to_items(array: Optional[np.ndarray]) -> Tuple[int, ...]:
    if array is None:
        return ()
    return tuple(int(value) for value in array)


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

    Each dimension becomes an :class:`InstrumentSequence`; a dimension with no data
    becomes a disabled (empty) sequence. When ``loop`` is set, every populated
    sequence loops from its first item so the instrument sustains on a held note.

    Raw arrays are taken directly (rather than a ``Features`` instance) to keep this
    module free of a dependency on the exporter layer.
    """
    arrays: Dict[SequenceKind, Optional[np.ndarray]] = {
        SequenceKind.VOLUME: volume,
        SequenceKind.ARPEGGIO: arpeggio,
        SequenceKind.PITCH: pitch,
        SequenceKind.HI_PITCH: hi_pitch,
        SequenceKind.DUTY: duty_cycle,
    }

    sequences: Dict[SequenceKind, InstrumentSequence] = {}
    for kind, array in arrays.items():
        items = _to_items(array)
        loop_point = LOOP_FROM_START if loop and items else NO_LOOP_POINT
        sequences[kind] = InstrumentSequence(kind=kind, items=items, loop_point=loop_point)

    return sequences
