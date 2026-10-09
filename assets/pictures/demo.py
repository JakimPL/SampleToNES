from pathlib import Path
from typing import Final

from assets.demo.paths import (
    PROJECTS_FOLDER,
    RECONSTRUCTIONS_FOLDER,
    RECORDINGS_FOLDER,
)
from assets.demo.specification import DemoSpecification
from sampletones_shared.paths.extensions import (
    EXT_FILE_PROJECT,
    EXT_FILE_RECONSTRUCTION,
    EXT_FILE_WAVE,
)
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS

SPECIFICATION: Final[DemoSpecification] = DemoSpecification.load()
PIECE: Final[str] = SPECIFICATION.recordings.piece.name
PROJECT: Final[str] = SPECIFICATION.project.module.title


def recordings_folder() -> Path:
    """The demo's recordings, laid beside the working directory the application was started in."""
    return Path.cwd() / RECORDINGS_FOLDER


def piece_folder() -> Path:
    """The folder holding the piece's stems, inside the recordings."""
    return recordings_folder() / PIECE


def hit_recording(name: str) -> Path:
    """The recording of the hit ``name``."""
    return recordings_folder() / f"{name}{EXT_FILE_WAVE}"


def stem_recording(name: str) -> Path:
    """The recording of the piece's stem ``name``."""
    return piece_folder() / f"{name}{EXT_FILE_WAVE}"


def piece_document() -> Path:
    """The piece's reconstruction in the home's documents folder, under its configuration folder."""
    return next((USER_PATH_DOCUMENTS / RECONSTRUCTIONS_FOLDER).rglob(f"{PIECE}{EXT_FILE_RECONSTRUCTION}"))


def project_document() -> Path:
    """The demo project in the home's documents folder."""
    return USER_PATH_DOCUMENTS / PROJECTS_FOLDER / f"{PROJECT}{EXT_FILE_PROJECT}"
