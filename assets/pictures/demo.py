from pathlib import Path
from typing import Final

from assets.demo.paths import (
    RECORDINGS_FOLDER,
    hit_recording_path,
    piece_document_path,
    piece_folder_path,
    project_path,
    stem_recording_path,
)
from assets.demo.specification import DemoSpecification
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS

SPECIFICATION: Final[DemoSpecification] = DemoSpecification.load()
PIECE: Final[str] = SPECIFICATION.recordings.piece.name
PROJECT: Final[str] = SPECIFICATION.project.module.title


def recordings_folder() -> Path:
    """The demo's recordings, laid beside the working directory the application was started in."""
    return Path.cwd() / RECORDINGS_FOLDER


def piece_folder() -> Path:
    """The folder holding the piece's stems, inside the recordings."""
    return piece_folder_path(recordings_folder(), PIECE)


def hit_recording(name: str) -> Path:
    """The recording of the hit ``name``."""
    return hit_recording_path(recordings_folder(), name)


def stem_recording(name: str) -> Path:
    """The recording of the piece's stem ``name``."""
    return stem_recording_path(recordings_folder(), PIECE, name)


def piece_document() -> Path:
    """The piece's reconstruction in the home's documents folder, under its configuration folder."""
    return piece_document_path(USER_PATH_DOCUMENTS, PIECE)


def project_document() -> Path:
    """The demo project in the home's documents folder."""
    return project_path(USER_PATH_DOCUMENTS, PROJECT)
