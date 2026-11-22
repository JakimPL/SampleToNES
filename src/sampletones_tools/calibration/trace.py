from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Self, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstructor.decoder.base import (
    Alternatives,
    ChannelLattice,
    StemPools,
    Streams,
)
from sampletones_core.reconstructions.reconstructor.matching import ScoredCandidate

InstructionColumn = Tuple[InstructionUnion, ...]
InstructionCombination = Tuple[InstructionUnion, ...]


@dataclass(frozen=True)
class PoolTrace:
    """What a stem's pools offered a decoder over whole combinations, frame by frame.

    Attributes:
        channel_names: The stem's channels, in the order every combination lists them.
        frames: Each frame's combinations, each the instructions of the stem's channels.
    """

    channel_names: Tuple[ChannelName, ...]
    frames: Tuple[Tuple[InstructionCombination, ...], ...]

    @classmethod
    def of(cls, pools: StemPools) -> Self:
        """The instructions of a stem's pools, frame by frame and combination by combination."""
        frames = tuple(tuple(_instructions(combination.candidates) for combination in pool) for pool in pools.frames)
        return cls(channel_names=pools.channel_names, frames=frames)


@dataclass(frozen=True)
class SearchTrace:
    """What a conversion's search offered and chose, frame by frame, before refinement.

    Attributes:
        columns: Every channel's column per frame, the assignment's pick first, then the alternatives
            the decoder could take.
        pools: Every stem's pools, keyed by stem id; an assignment of one channel at a time pools none.
        decoded: Every channel's decoded instruction per frame.
    """

    columns: Dict[ChannelName, Tuple[InstructionColumn, ...]]
    pools: Dict[int, PoolTrace]
    decoded: Dict[ChannelName, Tuple[InstructionUnion, ...]]


class TraceRecorder:
    """Keeps the instructions a conversion's search offered and decoded, which a search reading reads.

    Only the instructions are kept, so a trace of a long sound holds what the reading compares and
    leaves the scoring behind.
    """

    def __init__(self) -> None:
        self._columns: Optional[Dict[ChannelName, Tuple[InstructionColumn, ...]]] = None
        self._pools: Dict[int, PoolTrace] = {}
        self._decoded: Optional[Dict[ChannelName, Tuple[InstructionUnion, ...]]] = None

    def assigned(self, alternatives: Alternatives) -> None:
        """Keeps what the assignment left the decoder: every channel's columns and every stem's pools."""
        self._columns = {channel: _lattice_instructions(lattice) for channel, lattice in alternatives.lattices.items()}
        self._pools = {stem_id: PoolTrace.of(stem_pools) for stem_id, stem_pools in alternatives.pools.items()}

    def decoded(self, streams: Streams) -> None:
        """Keeps what the decoder chose for every channel, frame by frame."""
        self._decoded = {channel: _instructions(stream) for channel, stream in streams.items()}

    @property
    def trace(self) -> Optional[SearchTrace]:
        """The trace of the conversion heard, or ``None`` before it reached its decoding."""
        if self._columns is None or self._decoded is None:
            return None

        return SearchTrace(columns=self._columns, pools=self._pools, decoded=self._decoded)


def _lattice_instructions(lattice: ChannelLattice) -> Tuple[InstructionColumn, ...]:
    """A channel's columns as their candidates' instructions, frame by frame."""
    return tuple(_instructions(column) for column in lattice)


def _instructions(candidates: Iterable[ScoredCandidate]) -> Tuple[InstructionUnion, ...]:
    """The instructions of scored candidates, in their order."""
    return tuple(candidate.instruction for candidate in candidates)
