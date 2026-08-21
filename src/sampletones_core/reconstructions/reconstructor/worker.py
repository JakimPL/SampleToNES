from dataclasses import dataclass, field
from typing import Dict

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Window
from sampletones_core.fft.features import FeatureExtractor, get_feature_extractor
from sampletones_core.generators import GeneratorUnion
from sampletones_core.library import InstructionLibraryData

from .candidates import CandidateProvider
from .decoder import DECODERS, Decoder
from .matching import FrameMatcher
from .phase import PHASE_ALIGNERS, PhaseAligner
from .scorer import Scorer


@dataclass(frozen=True)
class ReconstructorWorker:
    """
    Assembles the machinery one recording is matched and decoded with.

    Everything a reconstruction run needs beyond its target sits here, built once for the
    signal it will work on: the scorer and candidate provider the matching draws from, the
    phase aligner and feature extractor it measures with, the `FrameMatcher` the stems
    assignment scores through, and the `Decoder` the configuration names.
    """

    config: Config
    window: Window
    channels: Dict[ChannelName, GeneratorUnion]
    library_data: InstructionLibraryData
    signal_length: int

    scorer: Scorer = field(init=False)
    candidate_provider: CandidateProvider = field(init=False)
    phase_aligner: PhaseAligner = field(init=False)
    feature_extractor: FeatureExtractor = field(init=False)
    matcher: FrameMatcher = field(init=False)
    decoder: Decoder = field(init=False)

    def __post_init__(self) -> None:
        scorer = Scorer(self.config, self.window, self.signal_length)
        candidate_provider = CandidateProvider(self.config, self.window, self.library_data)
        phase_aligner_class = PHASE_ALIGNERS[self.config.generation.calculation.phase_aligner]
        phase_aligner = phase_aligner_class(self.config, self.window, self.library_data)
        feature_extractor = get_feature_extractor(self.config, self.window)
        matcher = FrameMatcher(
            config=self.config,
            candidate_provider=candidate_provider,
            scorer=scorer,
            phase_aligner=phase_aligner,
        )
        decoder_class = DECODERS[self.config.generation.decoder.selector]

        object.__setattr__(self, "scorer", scorer)
        object.__setattr__(self, "candidate_provider", candidate_provider)
        object.__setattr__(self, "phase_aligner", phase_aligner)
        object.__setattr__(self, "feature_extractor", feature_extractor)
        object.__setattr__(self, "matcher", matcher)
        object.__setattr__(self, "decoder", decoder_class(self.config))
