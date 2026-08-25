import itertools
from typing import List, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.instructions import InstructionUnion

from ..matching import ScoredCandidate
from .base import ChannelLattice, Decoder, Lattices, Streams


class ViterbiDecoder(Decoder):
    """
    Plays the cheapest path through each channel's frames, cost and continuity together.

    A frame's candidates are weighed against the frames around them: on top of each
    candidate's own cost, moving between two candidates costs what changes between their
    instructions — pitch, volume, timbre, and turning a channel on or off. The path that
    minimizes the total holds a steady note where per-frame costs alone would flicker.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        decoder = config.generation.decoder
        self.pitch_weight = decoder.pitch_weight
        self.volume_weight = decoder.volume_weight
        self.timbre_weight = decoder.timbre_weight
        self.on_off_weight = decoder.on_off_weight

    @property
    def lattice_width(self) -> int:
        return self.config.generation.decoder.top_k

    def decode(self, lattices: Lattices) -> Streams:
        return {channel_name: self._decode_channel(frames) for channel_name, frames in lattices.items()}

    def _decode_channel(self, frames: ChannelLattice) -> List[ScoredCandidate]:
        path = self._decode(frames)
        return [frames[position][state] for position, state in enumerate(path)]

    def _decode(self, frames: ChannelLattice) -> List[int]:
        if not frames:
            return []

        backpointers, final_costs = self._forward_pass(frames)
        return self._backtrack(backpointers, final_costs)

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
            total = previous_costs[index] + self._transition_cost(previous_state.instruction, instruction)
            if total < best_cost:
                best_cost = total
                best_index = index

        return best_index, best_cost

    def _backtrack(self, backpointers: List[List[int]], final_costs: List[float]) -> List[int]:
        last = int(np.argmin(final_costs))
        path = [last]
        for layer in reversed(backpointers):
            last = layer[last]
            path.append(last)

        path.reverse()
        return path

    def _transition_cost(self, previous: InstructionUnion, current: InstructionUnion) -> float:
        if not previous.on and not current.on:
            return 0.0

        if previous.on != current.on:
            return self.on_off_weight

        cost = 0.0
        cost += self.pitch_weight * self._distance(previous, current, "pitch")
        cost += self.pitch_weight * self._distance(previous, current, "period")
        cost += self.volume_weight * self._distance(previous, current, "volume")
        cost += self.timbre_weight * self._mismatch(previous, current, "duty_cycle")
        cost += self.timbre_weight * self._mismatch(previous, current, "short")
        return cost

    @staticmethod
    def _distance(previous: InstructionUnion, current: InstructionUnion, field: str) -> float:
        previous_value = getattr(previous, field, None)
        current_value = getattr(current, field, None)
        if previous_value is None or current_value is None:
            return 0.0

        return float(abs(int(previous_value) - int(current_value)))

    @staticmethod
    def _mismatch(previous: InstructionUnion, current: InstructionUnion, field: str) -> float:
        previous_value = getattr(previous, field, None)
        current_value = getattr(current, field, None)
        if previous_value is None or current_value is None:
            return 0.0

        return 0.0 if previous_value == current_value else 1.0
