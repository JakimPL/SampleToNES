from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.famitracker.model.instrument import Instrument2A03
from sampletones_core.famitracker.model.sequence import InstrumentSequence
from sampletones_core.famitracker.specification.sequences import (
    LOOP_FROM_START,
    MAX_SEQUENCES_PER_TYPE,
    NO_LOOP_POINT,
    SequenceKind,
)

SequenceReferences = Dict[Tuple[int, SequenceKind], int]


@dataclass(frozen=True)
class PooledSequence:
    """A shared sequence in the module pool, at its per-kind index."""

    kind: SequenceKind
    index: int
    sequence: InstrumentSequence


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

    Each dimension becomes an :class:`InstrumentSequence`; a dimension passed as
    ``None`` becomes a disabled (empty) sequence. When ``loop`` is set, every populated
    sequence loops from its first item so the instrument sustains on a held note.
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


def build_sequence_pool(
    instruments: Sequence[Instrument2A03],
) -> Tuple[List[PooledSequence], SequenceReferences]:
    """Pools every enabled instrument sequence, sharing identical ones.

    Sequences are deduplicated within each kind, so two instruments with the same
    volume envelope reference a single pooled entry. Returns the pool and a map from
    an instrument's index and sequence kind to the pooled per-kind index.
    """
    per_kind: Dict[SequenceKind, Dict[InstrumentSequence, int]] = {}
    pool: List[PooledSequence] = []
    references: SequenceReferences = {}

    for instrument in instruments:
        for kind in SequenceKind:
            sequence = instrument.sequences[kind]
            if not sequence.enabled:
                continue

            assigned = per_kind.setdefault(kind, {})
            index = assigned.get(sequence)
            if index is None:
                index = len(assigned)
                if index >= MAX_SEQUENCES_PER_TYPE:
                    raise ValueError(
                        f"Module exceeds the FamiTracker limit of {MAX_SEQUENCES_PER_TYPE} {kind.name} sequences"
                    )
                assigned[sequence] = index
                pool.append(PooledSequence(kind=kind, index=index, sequence=sequence))

            references[(instrument.index, kind)] = index

    return pool, references
