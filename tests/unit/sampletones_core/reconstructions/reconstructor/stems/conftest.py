from typing import Dict

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.reconstructions.reconstructor.selector.greedy import GreedySelector
from sampletones_core.reconstructions.reconstructor.selector.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.worker import ReconstructorWorker


@pytest.fixture(scope="module")
def matcher(worker: ReconstructorWorker) -> FrameMatcher:
    return FrameMatcher(
        config=worker.config,
        candidate_provider=worker.candidate_provider,
        scorer=worker.scorer,
        phase_aligner=worker.phase_aligner,
    )


@pytest.fixture(scope="module")
def all_channels(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, ChannelName.items())


@pytest.fixture(scope="module")
def greedy_selector(worker: ReconstructorWorker) -> GreedySelector:
    return _build_greedy_selector(worker, worker.channels)


@pytest.fixture(scope="module")
def all_channels_selector(
    worker: ReconstructorWorker,
    all_channels: Dict[ChannelName, GeneratorUnion],
) -> GreedySelector:
    return _build_greedy_selector(worker, all_channels)


def _build_greedy_selector(
    worker: ReconstructorWorker,
    channels: Dict[ChannelName, GeneratorUnion],
) -> GreedySelector:
    return GreedySelector(
        config=worker.config,
        window=worker.window,
        channels=channels,
        scorer=worker.scorer,
        candidate_provider=worker.candidate_provider,
        phase_aligner=worker.phase_aligner,
        feature_extractor=worker.feature_extractor,
    )
