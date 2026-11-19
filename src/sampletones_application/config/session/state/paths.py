from enum import StrEnum
from pathlib import Path
from typing import Dict, Self

from pydantic import BaseModel, Field, field_serializer

from sampletones_shared.paths.user import (
    CONFIG_PATH,
    PROJECTS_DIRECTORY,
    RECONSTRUCTIONS_DIRECTORY,
)


class LastPath(StrEnum):
    """A kind of file whose folder a dialog opens at next time, named as ``LastPaths`` names it."""

    RECONSTRUCTION = "reconstruction"
    AUDIO_INPUT = "audio_input"
    CONFIG = "config"
    INSTRUMENT = "instrument"
    AUDIO = "audio"
    PROJECT = "project"


class LastPaths(BaseModel):
    reconstruction: Path = Field(
        default=RECONSTRUCTIONS_DIRECTORY,
        description="The last used directory of saved reconstruction files.",
    )
    audio_input: Path = Field(
        default=Path.home(),
        description="The last used directory of audio chosen for reconstruction.",
    )
    config: Path = Field(
        default=CONFIG_PATH.parent,
        description="The last used configuration file path.",
    )
    instrument: Path = Field(
        default=Path.cwd(),
        description="The last used FamiTracker instrument file path.",
    )
    audio: Path = Field(
        default=Path.cwd(),
        description="The last used WAV export file path.",
    )
    project: Path = Field(
        default=PROJECTS_DIRECTORY,
        description="The last used project directory path.",
    )

    @field_serializer(
        "reconstruction",
        "audio_input",
        "config",
        "instrument",
        "audio",
        "project",
    )
    def serialize_paths(self, path: Path) -> str:
        return str(path)

    def folder(self, kind: LastPath) -> Path:
        """The folder the last file of ``kind`` was chosen in."""
        folders: Dict[LastPath, Path] = {
            LastPath.RECONSTRUCTION: self.reconstruction,
            LastPath.AUDIO_INPUT: self.audio_input,
            LastPath.CONFIG: self.config,
            LastPath.INSTRUMENT: self.instrument,
            LastPath.AUDIO: self.audio,
            LastPath.PROJECT: self.project,
        }
        return folders[kind]

    def with_folder(self, kind: LastPath, folder: Path) -> Self:
        """These folders with the one for ``kind`` replaced by ``folder``."""
        return self.model_copy(update={kind.value: folder})
