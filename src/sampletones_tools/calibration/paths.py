from pathlib import Path
from typing import Final, Tuple

from sampletones_shared.paths.package import package_directory

CALIBRATION_CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.calibration.config")
REFEREE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "referee.yaml"
CORPUS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "corpus.yaml"
SEQUENCES_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "sequences.yaml"
NOTES_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "notes.yaml"
PITCHED_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "pitched.yaml"
TRUTH_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "truth.yaml"
SAMPLES_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "samples.yaml"
CHORDS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "chords.yaml"
SUITE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "suite.yaml"
SETTINGS_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "settings.yaml"
SOURCE_PACKAGES: Final[Tuple[str, ...]] = ("sampletones_core", "sampletones_shared", "sampletones_tools")
SOURCE_DIRECTORIES: Final[Tuple[Path, ...]] = tuple(package_directory(package) for package in SOURCE_PACKAGES)
