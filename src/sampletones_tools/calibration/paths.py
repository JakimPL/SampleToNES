from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory

CALIBRATION_CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.calibration.config")
REFEREE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "referee.yaml"
CORPUS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "corpus.yaml"
SEQUENCES_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "sequences.yaml"
NOTES_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "notes.yaml"
PITCHED_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "pitched.yaml"
SAMPLES_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "samples.yaml"
CHORDS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "chords.yaml"
SUITE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "suite.yaml"
SETTINGS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "settings.yaml"
