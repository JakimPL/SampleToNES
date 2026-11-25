from pathlib import Path
from typing import Final, FrozenSet
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, LevelMethod
from sampletones_core.fft import Window
from sampletones_core.library import InstructionLibrary
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.levels import (
    TRUE_LEVEL_COEFFICIENT,
    TrueLevel,
    level_config,
    level_reconstructor,
)
from sampletones_tools.corpus.catalog import build_mini_library

LOUD_SAMPLE: Final[float] = 0.9
RECORDING_SAMPLES: Final[int] = 4096
ONE_PER_GENERATOR: Final[int] = 1
EVERY_CHANNEL: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


@pytest.fixture(name="stored")
def stored_fixture(tmp_path: Path) -> Config:
    """A configuration whose library directory holds a library of one instruction per generator."""
    config = Config()
    config = config.model_copy(
        update={"general": config.general.model_copy(update={"library_directory": str(tmp_path)})}
    )
    library = build_mini_library(config, per_generator=ONE_PER_GENERATOR)
    key = library.create_key(config, Window.from_config(config))
    InstructionLibrary.from_config(config).save_data(key, library.data[key])
    return config


class TestLevelConfig:
    def test_the_default_level_converts_under_the_configuration_as_given(self) -> None:
        config = Config()

        assert level_config(config, VariantLevel.DEFAULT) == config

    def test_the_true_level_reads_files_as_they_are(self) -> None:
        config = level_config(Config(), VariantLevel.TRUE)

        assert config.general.normalize is False
        assert config.generation == Config().generation


class TestTheTrueLevel:
    def test_any_sound_is_matched_at_the_level_its_file_holds(self) -> None:
        stems = StemsConfig.single_entry(StemSettings.covering([ChannelName.PULSE1]))
        loud = np.full(RECORDING_SAMPLES, LOUD_SAMPLE)

        assert TrueLevel().coefficient([loud], stems, MagicMock(spec=FrameMatcher)) == TRUE_LEVEL_COEFFICIENT

    @pytest.mark.parametrize("method", list(LevelMethod))
    def test_a_reconstructor_at_the_true_level_matches_there_under_every_level_method(
        self, stored: Config, method: LevelMethod
    ) -> None:
        config = stored.model_copy(update={"general": stored.general.model_copy(update={"level": method})})

        reconstructor = level_reconstructor(level_config(config, VariantLevel.TRUE), EVERY_CHANNEL, VariantLevel.TRUE)

        assert type(reconstructor.level) is TrueLevel
