from pathlib import Path
from typing import Final

from sampletones_shared.paths.resources import CONFIG_DIRECTORY

CALIBRATION_CONFIG_DIRECTORY: Final[Path] = CONFIG_DIRECTORY / "calibration"
REFEREE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "referee.yaml"
CORPUS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "corpus.yaml"
