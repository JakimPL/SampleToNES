from dataclasses import dataclass, field
from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import GeneratorClassName, GeneratorName
from sampletones_core.fft import Fragment, FragmentedAudio, Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_remaining_generator_classes,
)
from sampletones_core.library import InstructionLibraryData

from .approximation import ApproximationData
from .candidates import CandidateProvider
from .phase import PHASE_ALIGNERS, PhaseAligner
from .scorer import Scorer
from .selector import SELECTORS, Selector


@dataclass(frozen=True)
class ReconstructorWorker:
    config: Config
    window: Window
    generators: Dict[GeneratorName, GeneratorUnion]
    library_data: InstructionLibraryData
    signal_length: int

    scorer: Scorer = field(init=False)
    candidate_provider: CandidateProvider = field(init=False)
    phase_aligner: PhaseAligner = field(init=False)
    feature_extractor: FeatureExtractor = field(init=False)
    selector: Selector = field(init=False)

    def __post_init__(self) -> None:
        scorer = Scorer(self.config, self.window, self.signal_length)
        candidate_provider = CandidateProvider(self.config, self.window, self.library_data)
        phase_aligner_class = PHASE_ALIGNERS[self.config.generation.calculation.phase_aligner]
        phase_aligner = phase_aligner_class(self.config, self.window, self.library_data)
        feature_extractor = get_feature_extractor(self.config, self.window)
        selector_class = SELECTORS[self.config.generation.decoder.selector]
        selector = selector_class(
            config=self.config,
            window=self.window,
            generators=self.generators,
            scorer=scorer,
            candidate_provider=candidate_provider,
            phase_aligner=phase_aligner,
            feature_extractor=feature_extractor,
        )

        object.__setattr__(self, "scorer", scorer)
        object.__setattr__(self, "candidate_provider", candidate_provider)
        object.__setattr__(self, "phase_aligner", phase_aligner)
        object.__setattr__(self, "feature_extractor", feature_extractor)
        object.__setattr__(self, "selector", selector)

    def __call__(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[GeneratorName, ApproximationData]]:
        return self.selector.select(fragmented_audio, fragment_ids)

    def reconstruct(self, fragment: Fragment) -> Dict[GeneratorName, ApproximationData]:
        return self.selector.reconstruct_fragment(fragment)

    def get_remaining_generator_classes(
        self,
        remaining_generators: Dict[GeneratorName, GeneratorUnion],
    ) -> Dict[GeneratorClassName, GeneratorUnion]:
        return get_remaining_generator_classes(remaining_generators)
