from pathlib import Path
from typing import FrozenSet

import pytest

from sampletones_core.configs import Config
from sampletones_core.configs.generation import GenerationConfig
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.library import InstructionLibrary
from sampletones_core.project.instruments.sample import Sample
from sampletones_core.project.project import Project
from sampletones_core.structures import IdentifiedCollection
from tests.integration.assets.reconstruction import build_mini_library, make_sample
from tests.integration.assets.song_loader import load_song
from tests.integration.assets.synth import synth_hihat, synth_kick

KICK_SLICES: FrozenSet[GeneratorName] = frozenset({GeneratorName.PULSE1, GeneratorName.TRIANGLE})
HIHAT_SLICES: FrozenSet[GeneratorName] = frozenset({GeneratorName.PULSE1, GeneratorName.PULSE2, GeneratorName.NOISE})
DRUM_PATTERN_PATH: Path = Path(__file__).parent / "assets" / "patterns" / "drum_pattern.json"


@pytest.fixture(scope="session")
def kick_config() -> Config:
    return Config(generation=GenerationConfig(generators=[GeneratorName.PULSE1, GeneratorName.TRIANGLE]))


@pytest.fixture(scope="session")
def hihat_config() -> Config:
    return Config(
        generation=GenerationConfig(generators=[GeneratorName.PULSE1, GeneratorName.PULSE2, GeneratorName.NOISE])
    )


@pytest.fixture(scope="session")
def sample_rate(kick_config: Config) -> int:
    return kick_config.library.sample_rate


@pytest.fixture(scope="session")
def mini_library(kick_config: Config) -> InstructionLibrary:
    return build_mini_library(kick_config)


@pytest.fixture(scope="session")
def audio_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("integration_audio")


@pytest.fixture(scope="session")
def kick_sample(
    kick_config: Config,
    mini_library: InstructionLibrary,
    audio_directory: Path,
    sample_rate: int,
) -> Sample:
    audio = synth_kick(sample_rate=sample_rate)
    return make_sample("kick", audio, kick_config, mini_library, tmp_dir=audio_directory, expected_slices=KICK_SLICES)


@pytest.fixture(scope="session")
def hihat_sample(
    hihat_config: Config,
    mini_library: InstructionLibrary,
    audio_directory: Path,
    sample_rate: int,
) -> Sample:
    audio = synth_hihat(sample_rate=sample_rate)
    return make_sample(
        "hihat", audio, hihat_config, mini_library, tmp_dir=audio_directory, expected_slices=HIHAT_SLICES
    )


@pytest.fixture(scope="session")
def integration_project(kick_sample: Sample, hihat_sample: Sample) -> Project:
    samples: IdentifiedCollection[Sample] = IdentifiedCollection()
    samples.append(kick_sample)
    samples.append(hihat_sample)

    project = Project.create(title="Drum Demo", author="Integration")
    project.samples = samples
    project.song = load_song(DRUM_PATTERN_PATH, {"kick": kick_sample, "hihat": hihat_sample})
    return project
