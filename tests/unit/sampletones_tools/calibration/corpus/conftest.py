from typing import Final, List

import pytest

from sampletones_tools.calibration.config.corpus import CorpusConfig
from sampletones_tools.calibration.config.truth import TruthConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.synthesis import build_corpus

SAMPLE_RATE: Final[int] = 22050
FRAME_RATE: Final[int] = 60


@pytest.fixture(scope="session")
def sample_rate() -> int:
    return SAMPLE_RATE


@pytest.fixture(scope="session")
def corpus_config() -> CorpusConfig:
    return CorpusConfig.load()


@pytest.fixture(scope="session")
def truth_config() -> TruthConfig:
    return TruthConfig.load()


@pytest.fixture(scope="session")
def corpus_items(corpus_config: CorpusConfig, truth_config: TruthConfig, sample_rate: int) -> List[CorpusItem]:
    return build_corpus(sample_rate, FRAME_RATE, config=corpus_config, truth=truth_config)
