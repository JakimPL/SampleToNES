from typing import Dict, Final

import pytest

from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_player.builder import song_from_reconstruction
from sampletones_player.compression.scheme import CompressionScheme
from sampletones_player.driver.image import DriverImage
from sampletones_player.song import Song
from sampletones_tools.corpus.build import Corpus, build_synthetic_corpus

EXPORTED_SAMPLE: Final[str] = "lead"


@pytest.fixture(scope="session")
def synthetic_corpus() -> Corpus:
    """The corpus the emitters and the report are built from, built once for the session."""
    return build_synthetic_corpus()


@pytest.fixture(scope="session")
def instrument_catalog(synthetic_corpus: Corpus) -> Dict[str, Sample]:
    return synthetic_corpus.catalog


@pytest.fixture(scope="session")
def integration_project(synthetic_corpus: Corpus) -> Project:
    return synthetic_corpus.project


@pytest.fixture(scope="session")
def driver_image() -> DriverImage:
    """The assembled driver every exported file carries."""
    return DriverImage.load()


@pytest.fixture
def sample(instrument_catalog: Dict[str, Sample]) -> Sample:
    """The sample the structural cases read, covering both pulse channels."""
    return instrument_catalog[EXPORTED_SAMPLE]


@pytest.fixture
def song(sample: Sample) -> Song:
    """The song the console plays that sample as."""
    return song_from_reconstruction(sample.reconstruction, loop_tick=None, scheme=CompressionScheme.SEARCH)
