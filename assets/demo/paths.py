from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.user import (
    CONFIG_PATH,
    LIBRARY_DIRECTORY,
    PROJECTS_DIRECTORY,
    RECONSTRUCTIONS_DIRECTORY,
)

CONFIG_DIRECTORY: Final[Path] = package_directory("assets.demo.config")
VOICES_PATH: Final[Path] = CONFIG_DIRECTORY / "voices.yaml"
RECORDINGS_PATH: Final[Path] = CONFIG_DIRECTORY / "recordings.yaml"
CONVERSION_PATH: Final[Path] = CONFIG_DIRECTORY / "conversion.yaml"
PROJECT_PATH: Final[Path] = CONFIG_DIRECTORY / "project.yaml"

RECORDINGS_FOLDER: Final[str] = "recordings"
LIBRARY_FOLDER: Final[str] = LIBRARY_DIRECTORY.name
RECONSTRUCTIONS_FOLDER: Final[str] = RECONSTRUCTIONS_DIRECTORY.name
PROJECTS_FOLDER: Final[str] = PROJECTS_DIRECTORY.name
CONFIG_FILE: Final[str] = CONFIG_PATH.name
