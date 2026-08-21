from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH

from .base import Decoder, Lattices, Streams


class GreedyDecoder(Decoder):
    """
    Plays each frame's best candidate, so every frame stands on its own.

    Reading one candidate per frame makes the frame's own cost the whole decision, which is
    the classic behaviour: what the matching ranked first is what the channel plays.
    """

    @property
    def lattice_width(self) -> int:
        return SINGLE_STATE_LATTICE_WIDTH

    def decode(self, lattices: Lattices) -> Streams:
        return {channel_name: [column[0] for column in frames] for channel_name, frames in lattices.items()}
