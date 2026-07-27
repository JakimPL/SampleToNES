from typing import Dict, List, Sequence, Tuple

from sampletones_core.famitracker.model.instrument import Instrument2A03
from sampletones_core.famitracker.model.sequence import InstrumentSequence
from sampletones_core.famitracker.sequences.pooled import PooledSequence
from sampletones_core.famitracker.specification.sequences import (
    MAX_SEQUENCES_PER_TYPE,
    SequenceKind,
)

SequenceReferences = Dict[Tuple[int, SequenceKind], int]


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
