from typing import Dict

import pytest

from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.corpus.build import Corpus, build_synthetic_corpus


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
