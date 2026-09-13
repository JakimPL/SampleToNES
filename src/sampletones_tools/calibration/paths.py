from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory

CALIBRATION_CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.calibration.config")
REFEREE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "referee.yaml"
CORPUS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "corpus.yaml"
