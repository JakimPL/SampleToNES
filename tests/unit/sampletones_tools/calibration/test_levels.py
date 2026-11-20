import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.levels import TRUE_LEVEL_COEFFICIENT, TrueLevelReconstructor, level_config


class TestLevelConfig:
    def test_the_default_level_converts_under_the_configuration_as_given(self) -> None:
        config = Config()

        assert level_config(config, WorkingLevel.DEFAULT) == config

    def test_the_true_level_reads_files_as_they_are(self) -> None:
        config = level_config(Config(), WorkingLevel.TRUE)

        assert config.general.normalize is False
        assert config.generation == Config().generation


class TestTrueLevelReconstructor:
    def test_any_sound_is_matched_at_the_level_its_file_holds(self) -> None:
        reconstructor = TrueLevelReconstructor.__new__(TrueLevelReconstructor)
        stems = StemsConfig.single_entry(StemSettings.covering([ChannelName.PULSE1]))
        loud = np.full(4096, 0.9)

        assert reconstructor.get_coefficient(loud, stems) == TRUE_LEVEL_COEFFICIENT
