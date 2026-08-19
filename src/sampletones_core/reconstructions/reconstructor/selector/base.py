from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment, FragmentedAudio, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
    get_remaining_generator_classes,
)
from sampletones_core.instructions import InstructionUnion

from ..approximation import ApproximationData
from ..candidates import CandidateProvider
from ..phase import PhaseAligner
from ..scorer import Scorer


@dataclass(frozen=True)
class ScoredCandidate:
    instruction: InstructionUnion
    cost: float
    approximation: Fragment


class Selector(ABC):
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
        self.config = config
        self.window = window
        self.channels = channels
        self.scorer = scorer
        self.candidate_provider = candidate_provider
        self.phase_aligner = phase_aligner
        self.feature_extractor = feature_extractor
        self.top_k = config.generation.decoder.top_k

    @abstractmethod
    def select(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[ChannelName, ApproximationData]]: ...

    def reconstruct_fragment(self, fragment: Fragment) -> Dict[ChannelName, ApproximationData]:
        approximations: Dict[ChannelName, ApproximationData] = {}
        remaining_channels = dict(self.channels.items())
        while remaining_channels:
            remaining_generator_classes = get_remaining_generator_classes(remaining_channels)
            approximation_data = self._find_best_approximation(
                fragment,
                remaining_generator_classes,
            )
            fragment = self.feature_extractor.subtract(
                fragment,
                approximation_data.approximation,
            )
            approximations[approximation_data.channel_name] = approximation_data
            del remaining_channels[approximation_data.channel_name]

        return approximations

    def _score_candidates(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> List[ScoredCandidate]:
        """
        Score candidates in two stages: a phase-independent spectral shortlist, then a
        full ranking with the temporal term evaluated on each phase-aligned candidate.

        The shortlist ranks every candidate by the spectral term alone, which compares
        phase-averaged features and is therefore immune to how the candidate waveform
        happens to be phased. Each of the ``top_k`` shortlisted candidates is then built
        at its best phase against the target and receives the full criterion cost, so
        the temporal term measures waveform shape at the aligned phase. The aligned
        phase stands in for the rendered phase, which keeps oscillator continuity
        across frames.

        Args:
            fragment: Target fragment to match.
            remaining_generator_classes: Generators still available for this fragment.

        Returns:
            The shortlisted candidates with their aligned costs, best first.
        """
        valid_instructions, candidate_approximations = self.candidate_provider.candidates(remaining_generator_classes)
        spectral_costs = self.scorer.spectral_costs(fragment, candidate_approximations)
        shortlist = Scorer.top_k(spectral_costs, self.top_k)

        scored: List[ScoredCandidate] = []
        for index in shortlist:
            instruction = valid_instructions[index]
            generator = get_generator_by_instruction(instruction, remaining_generator_classes)
            approximation = self._build_approximation(fragment, instruction, generator)
            cost = self.scorer.aligned_cost(fragment, float(spectral_costs[index]), approximation)
            scored.append(ScoredCandidate(instruction=instruction, cost=cost, approximation=approximation))

        scored.sort(key=lambda candidate: candidate.cost)
        return scored

    def _find_best_approximation(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> ApproximationData:
        best = self._score_candidates(fragment, remaining_generator_classes)[0]
        generator = get_generator_by_instruction(best.instruction, remaining_generator_classes)

        return ApproximationData(
            channel_name=ChannelName(generator.name),
            approximation=best.approximation,
            instruction=best.instruction,
        )

    def _build_approximation(
        self,
        fragment: Fragment,
        instruction: InstructionUnion,
        generator: GeneratorUnion,
    ) -> Fragment:
        if self.config.generation.calculation.find_best_phase:
            return self.phase_aligner.align(fragment, instruction)
        return self.candidate_provider.get_approximation(instruction, generator)
