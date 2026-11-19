from pathlib import Path
from typing import Final

from sampletones_shared.paths.extensions import EXT_FILE_PROJECT, EXT_FILE_RECONSTRUCTION, EXT_FILE_WAVE
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


def hit_recording_path(recordings: Path, hit: str) -> Path:
    """Where the demo tree keeps the recording of the hit ``hit`` under the folder ``recordings``."""
    return recordings / f"{hit}{EXT_FILE_WAVE}"


def piece_folder_path(recordings: Path, piece: str) -> Path:
    """Where the demo tree keeps the stems of the piece ``piece`` under the folder ``recordings``."""
    return recordings / piece


def stem_recording_path(recordings: Path, piece: str, stem: str) -> Path:
    """Where the demo tree keeps the recording of the stem ``stem`` of the piece ``piece`` under ``recordings``."""
    return piece_folder_path(recordings, piece) / f"{stem}{EXT_FILE_WAVE}"


def project_path(documents: Path, title: str) -> Path:
    """Where the demo tree keeps the project ``title`` under the documents folder ``documents``."""
    return documents / PROJECTS_FOLDER / f"{title}{EXT_FILE_PROJECT}"


def piece_document_path(documents: Path, piece: str) -> Path:
    """The reconstruction of the piece ``piece`` under the documents folder ``documents``, in its configuration
    folder.
    """
    return next((documents / RECONSTRUCTIONS_FOLDER).rglob(f"{piece}{EXT_FILE_RECONSTRUCTION}"))
