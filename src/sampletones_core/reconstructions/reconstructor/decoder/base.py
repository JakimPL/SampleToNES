from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName

from ..matching import Column, ScoredCandidate

ChannelLattice = List[Column]
Lattices = Dict[ChannelName, ChannelLattice]
Streams = Dict[ChannelName, List[ScoredCandidate]]


@dataclass(frozen=True)
class PooledCombination:
    """One whole answer for a stem's channels in one frame.

    Attributes:
        candidates: What each of the stem's channels plays, in the order its pools name the channels,
            each scored at the combination's cost.
        cost: What the assignment weighs the combination by: the full cost of the stem's frame with
            it sounding, and the charge for breaking with the frames beside it where a neighbor pass
            charges one.
    """

    candidates: Tuple[ScoredCandidate, ...]
    cost: float


Pool = Tuple[PooledCombination, ...]


@dataclass(frozen=True)
class StemPools:
    """One stem's whole combinations across a recording's frames, one pool per frame.

    Attributes:
        channel_names: The stem's channels, in the order every combination lists them.
        frames: Each frame's pool, in frame order.
    """

    channel_names: Tuple[ChannelName, ...]
    frames: List[Pool]


Pools = Dict[int, StemPools]


@dataclass(frozen=True)
class Alternatives:
    """What a recording's assignment leaves the decoder to choose from, frame by frame.

    Attributes:
        lattices: Every channel's column per frame, best first.
        pools: Every stem's whole combinations per frame, keyed by stem id. An assignment that answers
            one channel at a time offers none.
    """

    lattices: Lattices
    pools: Pools


class Decoder(ABC):
    """
    Chooses what each channel plays across the frames it was given.

    A frame assignment hands every channel in play one column per frame: the candidates that
    channel may sound there, best first, at least one of them. A joint assignment also hands every
    stem a pool of whole combinations per frame. A decoder reads those alternatives and answers one
    candidate per frame per channel, which is the instruction stream the reconstruction records.
    Ownership is settled before a decoder sees the frames, so a decoder decides the stream alone.

    A candidate's or a combination's cost is what the assignment weighs it by. In a neighbor pass
    with inertia that holds the charge for breaking with the frames beside it, so a decoder adding
    its own transitions between frames reads that charge as part of every frame's cost.

    ``lattice_width`` states how many alternatives per frame the decoder reads, and the
    assignment builds columns to exactly that width, so a decoder that reads one candidate
    per frame costs the assignment nothing beyond the pick it already made.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    @property
    @abstractmethod
    def lattice_width(self) -> int:
        """How many candidates per frame the decoder chooses among."""

    @abstractmethod
    def decode(self, alternatives: Alternatives) -> Streams:
        """One candidate per frame for every channel, in frame order."""
