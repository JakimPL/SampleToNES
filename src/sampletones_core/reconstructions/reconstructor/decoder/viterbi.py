import itertools
from typing import List, Tuple

from sampletones_core.configs import Config
from sampletones_core.instructions import InstructionUnion

from ..matching import ScoredCandidate
from .base import Alternatives, ChannelLattice, Decoder, Streams
from .path import traced_back
from .transition import TransitionWeights, transition_cost


class ViterbiDecoder(Decoder):
    """
    Plays the cheapest path through each channel's frames, cost and continuity together.

    A frame's candidates are weighed against the frames around them: on top of each
    candidate's own cost, moving between two candidates costs what changes between their
    instructions — pitch, volume, timbre, and turning a channel on or off. The path that
    minimizes the total holds a steady note where per-frame costs alone would flicker.

    A tie goes to the earlier candidate of a column: a candidate is reached from the earliest of
    equally cheap predecessors, and the path ends on the earliest of equally cheap last candidates.
    A column lists a channel's silence ahead of an equal cost, so the silence takes such a tie.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.weights = TransitionWeights.of(config)

    @property
    def lattice_width(self) -> int:
        return self.config.generation.decoder.top_k

    def decode(self, alternatives: Alternatives) -> Streams:
        return {channel_name: self._decode_channel(frames) for channel_name, frames in alternatives.lattices.items()}

    def _decode_channel(self, frames: ChannelLattice) -> List[ScoredCandidate]:
        path = self._decode(frames)
        return [frames[position][state] for position, state in enumerate(path)]

    def _decode(self, frames: ChannelLattice) -> List[int]:
        if not frames:
            return []

        backpointers, final_costs = self._forward_pass(frames)
        return traced_back(backpointers, final_costs)

    def _forward_pass(self, frames: ChannelLattice) -> Tuple[List[List[int]], List[float]]:
        costs = [state.cost for state in frames[0]]
        backpointers: List[List[int]] = []

        for previous_states, current_states in itertools.pairwise(frames):
            layer_costs: List[float] = []
            layer_backpointers: List[int] = []
            for state in current_states:
                predecessor, accumulated = self._best_predecessor(costs, previous_states, state.instruction)
                layer_costs.append(accumulated + state.cost)
                layer_backpointers.append(predecessor)

            costs = layer_costs
            backpointers.append(layer_backpointers)

        return backpointers, costs

    def _best_predecessor(
        self,
        previous_costs: List[float],
        previous_states: Tuple[ScoredCandidate, ...],
        instruction: InstructionUnion,
    ) -> Tuple[int, float]:
        best_index = 0
        best_cost = float("inf")
        for index, previous_state in enumerate(previous_states):
            total = previous_costs[index] + transition_cost(previous_state.instruction, instruction, self.weights)
            if total < best_cost:
                best_cost = total
                best_index = index

        return best_index, best_cost
