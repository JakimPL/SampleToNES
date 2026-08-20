from abc import ABC, abstractmethod
from typing import Dict, List

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment, FragmentedAudio, Window
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_remaining_generator_classes,
)

from ..approximation import ApproximationData
from ..candidates import CandidateProvider
from ..phase import PhaseAligner
from ..scorer import Scorer
from .matching import FrameMatcher, ScoredCandidate


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
        self.matcher = FrameMatcher(
            config=config,
            candidate_provider=candidate_provider,
            scorer=scorer,
            phase_aligner=phase_aligner,
        )

    @abstractmethod
    def select(
        self,
        fragmented_audio: FragmentedAudio,
        fragment_ids: List[int],
    ) -> Dict[int, Dict[ChannelName, ApproximationData]]: ...

    def reconstruct_fragment(
        self,
        fragment: Fragment,
    ) -> Dict[ChannelName, ApproximationData]:
        approximations: Dict[ChannelName, ApproximationData] = {}
        remaining_channels = dict(self.channels.items())
        while remaining_channels:
            remaining_generator_classes = get_remaining_generator_classes(remaining_channels)
            approximation_data = self.matcher.best_approximation(
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
        return self.matcher.score_candidates(fragment, remaining_generator_classes)
