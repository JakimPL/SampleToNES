from pathlib import Path
from typing import Dict

import pytest

from sampletones_core.project.project import Project
from sampletones_core.project.voices.sample import Sample
from sampletones_tools.corpus.build import build_project
from sampletones_tools.corpus.catalog import CatalogSpec, build_catalog
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.corpus.song import SongSpec
from sampletones_tools.corpus.synth import SynthConfig


@pytest.fixture(scope="session")
def audio_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("integration_audio")


@pytest.fixture(scope="session")
def synth_config() -> SynthConfig:
    return SynthConfig.load()


@pytest.fixture(scope="session")
def module_config() -> ModuleConfig:
    return ModuleConfig.load()


@pytest.fixture(scope="session")
def instrument_catalog(audio_directory: Path, synth_config: SynthConfig) -> Dict[str, Sample]:
    return build_catalog(CatalogSpec.load(), synth_config, tmp_dir=audio_directory)


@pytest.fixture(scope="session")
def integration_project(instrument_catalog: Dict[str, Sample], module_config: ModuleConfig) -> Project:
    return build_project(instrument_catalog, module_config, SongSpec.load())
