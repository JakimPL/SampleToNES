import itertools
from typing import Dict, List, Tuple

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment, FragmentedAudio, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion

from ..approximation import ApproximationData
from ..candidates import CandidateProvider
from ..phase import PhaseAligner
from ..scorer import Scorer
from .base import ScoredCandidate, Selector

ChannelLattice = List[List[ScoredCandidate]]
FrameCandidates = Dict[ChannelName, List[ScoredCandidate]]


class ViterbiSelector(Selector):
    def __init__(
        self,
        config: Config,
        window: Window,
        channels: Dict[ChannelName, GeneratorUnion],
        scorer: Scorer,
        candidate_provider: CandidateProvider,
        phase_aligner: PhaseAligner,
        feature_extractor: FeatureExtractor,
    ) -> None:
        super().__init__(
            config,
            window,
            channels,
            scorer,
            candidate_provider,
            phase_aligner,
            feature_extractor,
        )
        decoder = config.generation.decoder
        self.pitch_weight = decoder.pitch_weight
        self.volume_weight = decoder.volume_weight
        self.timbre_weight = decoder.timbre_weight
        self.on_off_weight = decoder.on_off_weight

    def select(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[ChannelName, ApproximationData]]:
        lattices = self._build_lattices(fragmented_audio, fragment_ids)
        return self._decode_lattices(lattices, fragment_ids)

    def _build_lattices(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[ChannelName, ChannelLattice]:
        lattices: Dict[ChannelName, ChannelLattice] = {name: [] for name in self.channels}
        for fragment_id in fragment_ids:
            for channel_name, states in self._frame_candidates(fragmented_audio[fragment_id]).items():
                lattices[channel_name].append(states)

        return lattices

    def _decode_lattices(
        self,
        lattices: Dict[ChannelName, ChannelLattice],
        fragment_ids: List[int],
    ) -> Dict[int, Dict[ChannelName, ApproximationData]]:
        result: Dict[int, Dict[ChannelName, ApproximationData]] = {fragment_id: {} for fragment_id in fragment_ids}
        for channel_name, frames in lattices.items():
            path = self._decode(frames)
            for position, fragment_id in enumerate(fragment_ids):
                state = frames[position][path[position]]
                result[fragment_id][channel_name] = ApproximationData(
                    channel_name=channel_name,
                    approximation=state.approximation,
                    instruction=state.instruction,
                )

        return result

    def _frame_candidates(self, fragment: Fragment) -> FrameCandidates:
        candidates: FrameCandidates = {}
        residual = fragment
        for channel_name, generator in self.channels.items():
            channel_states = self._channel_candidates(residual, generator)
            candidates[channel_name] = channel_states
            residual = self.feature_extractor.subtract(residual, channel_states[0].approximation)

        return candidates

    def _channel_candidates(self, residual: Fragment, generator: GeneratorUnion) -> List[ScoredCandidate]:
        return self._score_candidates(residual, {generator.class_name(): generator})

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
        previous_states: List[ScoredCandidate],
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
