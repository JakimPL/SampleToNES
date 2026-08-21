from typing import Dict

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import SINGLE_STATE_LATTICE_WIDTH
from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.fft.features import FeatureExtractor
from sampletones_core.generators import (
    GeneratorUnion,
    get_generator_by_instruction,
    get_generators_by_channels,
    get_remaining_generator_classes,
)
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


@pytest.fixture(scope="module")
def matcher(worker: ReconstructorWorker) -> FrameMatcher:
    return worker.matcher


@pytest.fixture(scope="module")
def all_channels(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, ChannelName.items())


def greedy_baseline(
    fragment: Fragment,
    channels: Dict[ChannelName, GeneratorUnion],
    matcher: FrameMatcher,
    extractor: FeatureExtractor,
) -> Dict[ChannelName, ScoredCandidate]:
    """The classic per-frame reconstruction, restated here as the assignment's reference.

    Takes the cheapest candidate across every channel still free, subtracts it from the
    residual, and repeats until each channel is answered. A one-stem setup at full cap runs
    exactly this order, which is what makes the two comparable frame by frame.
    """
    answers: Dict[ChannelName, ScoredCandidate] = {}
    remaining_channels = dict(channels)
    residual = fragment
    while remaining_channels:
        remaining_generator_classes = get_remaining_generator_classes(remaining_channels)
        best = matcher.score_candidates(residual, remaining_generator_classes)[0]
        generator = get_generator_by_instruction(best.instruction, remaining_generator_classes)
        channel_name = ChannelName(generator.name)
        answers[channel_name] = best
        residual = extractor.subtract(residual, best.approximation)
        del remaining_channels[channel_name]

    return answers


@pytest.fixture(scope="module")
def lattice_width() -> int:
    """The width a greedy decoder reads, which is what the equivalence baseline assumes."""
    return SINGLE_STATE_LATTICE_WIDTH
