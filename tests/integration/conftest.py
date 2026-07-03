from pathlib import Path
from typing import Dict

import pytest

from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.structures import IdentifiedCollection
from tests.integration.assets.module_config import ModuleConfig, load_module_config
from tests.integration.assets.reconstruction import load_instrument_catalog
from tests.integration.assets.song_loader import load_song
from tests.integration.assets.synth_config import SynthConfig, load_synth_config
from tests.integration.paths import (
    MODULE_CONFIG_PATH,
    RECONSTRUCTION_CONFIG_PATH,
    SONG_PATH,
    SYNTH_CONFIG_PATH,
)


@pytest.fixture(scope="session")
def audio_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("integration_audio")


@pytest.fixture(scope="session")
def synth_config() -> SynthConfig:
    return load_synth_config(SYNTH_CONFIG_PATH)


@pytest.fixture(scope="session")
def module_config() -> ModuleConfig:
    return load_module_config(MODULE_CONFIG_PATH)


@pytest.fixture(scope="session")
def instrument_catalog(audio_directory: Path, synth_config: SynthConfig) -> Dict[str, Sample]:
    return load_instrument_catalog(RECONSTRUCTION_CONFIG_PATH, synth_config, tmp_dir=audio_directory)


@pytest.fixture(scope="session")
def integration_project(instrument_catalog: Dict[str, Sample], module_config: ModuleConfig) -> Project:
    samples: IdentifiedCollection[Sample] = IdentifiedCollection()
    for sample in instrument_catalog.values():
        samples.append(sample)

    settings = ProjectSettings(
        tempo=module_config.tempo,
        speed=module_config.speed,
        nes_frequency=module_config.nes_frequency,
    )
    project = Project.create(title=module_config.title, author=module_config.author, settings=settings)
    project.samples = samples
    project.song = load_song(SONG_PATH, instrument_catalog)
    return project
