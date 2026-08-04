from dataclasses import dataclass

from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind


@dataclass(frozen=True)
class PooledSequence:
    """A shared sequence in the module pool, at its per-kind index."""

    kind: SequenceKind
    index: int
    sequence: InstrumentSequence
