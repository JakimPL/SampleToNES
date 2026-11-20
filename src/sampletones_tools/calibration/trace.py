from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstructor.decoder.base import Lattices, Streams

InstructionColumn = Tuple[InstructionUnion, ...]


@dataclass(frozen=True)
class SearchTrace:
    """What a conversion's search offered and chose, frame by frame, before refinement.

    Attributes:
        columns: Every channel's column per frame, the assignment's pick first, then the alternatives
            the decoder could take.
        decoded: Every channel's decoded instruction per frame.
    """

    columns: Dict[ChannelName, Tuple[InstructionColumn, ...]]
    decoded: Dict[ChannelName, Tuple[InstructionUnion, ...]]


class TraceRecorder:
    """Keeps the instructions a conversion's search offered and decoded, which a search reading reads.

    Only the instructions are kept, so a trace of a long sound holds what the reading compares and
    leaves the scoring behind.
    """

    def __init__(self) -> None:
        self._columns: Optional[Dict[ChannelName, Tuple[InstructionColumn, ...]]] = None
        self._decoded: Optional[Dict[ChannelName, Tuple[InstructionUnion, ...]]] = None

    def assigned(self, lattices: Lattices) -> None:
        self._columns = {
            channel: tuple(tuple(candidate.instruction for candidate in column) for column in lattice)
            for channel, lattice in lattices.items()
        }

    def decoded(self, streams: Streams) -> None:
        self._decoded = {
            channel: tuple(candidate.instruction for candidate in stream) for channel, stream in streams.items()
        }

    @property
    def trace(self) -> Optional[SearchTrace]:
        """The trace of the conversion heard, or ``None`` before it reached its decoding."""
        if self._columns is None or self._decoded is None:
            return None

        return SearchTrace(columns=self._columns, decoded=self._decoded)
