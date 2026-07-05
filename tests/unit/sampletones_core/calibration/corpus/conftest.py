from typing import Final, List

import pytest

from sampletones_core.calibration.config.corpus import CorpusConfig
from sampletones_core.calibration.corpus.item import CorpusItem
from sampletones_core.calibration.corpus.synthesis import build_corpus

SAMPLE_RATE: Final[int] = 22050


@pytest.fixture(scope="session")
def sample_rate() -> int:
    return SAMPLE_RATE


@pytest.fixture(scope="session")
def corpus_config() -> CorpusConfig:
    return CorpusConfig.load()


@pytest.fixture(scope="session")
def corpus_items(corpus_config: CorpusConfig, sample_rate: int) -> List[CorpusItem]:
    return build_corpus(sample_rate, config=corpus_config)
