from abc import ABC, abstractmethod
from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName

from ..matching import Column, ScoredCandidate

ChannelLattice = List[Column]
Lattices = Dict[ChannelName, ChannelLattice]
Streams = Dict[ChannelName, List[ScoredCandidate]]


class Decoder(ABC):
    """
    Chooses what each channel plays across the frames it was given.

    A frame assignment hands every channel in play one column per frame: the candidates that
    channel may sound there, best first. A decoder reads those columns and answers one candidate
    per frame per channel, which is the instruction stream the reconstruction records. Ownership
    is settled before a decoder sees the frames, so a decoder decides the stream alone.

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
    def decode(self, lattices: Lattices) -> Streams:
        """One candidate per frame for every channel, in frame order."""
