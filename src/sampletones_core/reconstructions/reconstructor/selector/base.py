from abc import ABC, abstractmethod
from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName, GeneratorName
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


class Selector(ABC):
    def __init__(
        self,
        config: Config,
        window: Window,
        generators: Dict[GeneratorName, GeneratorUnion],
        scorer: Scorer,
        candidate_provider: CandidateProvider,
        phase_aligner: PhaseAligner,
        feature_extractor: FeatureExtractor,
    ) -> None:
        self.config = config
        self.window = window
        self.generators = generators
        self.scorer = scorer
        self.candidate_provider = candidate_provider
        self.phase_aligner = phase_aligner
        self.feature_extractor = feature_extractor

    @abstractmethod
    def select(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[GeneratorName, ApproximationData]]: ...

    def reconstruct_fragment(self, fragment: Fragment) -> Dict[GeneratorName, ApproximationData]:
        approximations: Dict[GeneratorName, ApproximationData] = {}
        remaining_generators = dict(self.generators.items())
        while remaining_generators:
            remaining_generator_classes = get_remaining_generator_classes(remaining_generators)
            approximation_data = self._find_best_approximation(fragment, remaining_generator_classes)
            fragment = self.feature_extractor.subtract(fragment, approximation_data.approximation)
            approximations[approximation_data.generator_name] = approximation_data
            del remaining_generators[approximation_data.generator_name]

        return approximations

    def _find_best_approximation(
        self,
        fragment: Fragment,
        remaining_generator_classes: Dict[GeneratorClassName, GeneratorUnion],
    ) -> ApproximationData:
        valid_instructions, candidate_approximations = self.candidate_provider.candidates(remaining_generator_classes)
        index = self.scorer.best(fragment, candidate_approximations)
        instruction = valid_instructions[index]
        generator = get_generator_by_instruction(instruction, remaining_generator_classes)
        approximation = self._build_approximation(fragment, instruction, generator)

        return ApproximationData(
            generator_name=GeneratorName(generator.name),
            approximation=approximation,
            instruction=instruction,
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
