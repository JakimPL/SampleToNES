from importlib.resources import files
from pathlib import Path
from typing import Final

CALIBRATION_CONFIG_DIRECTORY: Final[Path] = Path(str(files("sampletones_tools.calibration.config")))
REFEREE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "referee.yaml"
CORPUS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "corpus.yaml"
