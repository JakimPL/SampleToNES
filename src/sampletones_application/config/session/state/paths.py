from pathlib import Path

from pydantic import BaseModel, Field, field_serializer

from sampletones_shared.paths.user import (
    CONFIG_PATH,
    LIBRARY_DIRECTORY,
    PROJECTS_DIRECTORY,
    RECONSTRUCTIONS_DIRECTORY,
)


class LastPaths(BaseModel):
    library: Path = Field(
        default=LIBRARY_DIRECTORY,
        description="The last used library directory path.",
    )
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
        "library",
        "reconstruction",
        "audio_input",
        "config",
        "instrument",
        "audio",
        "project",
    )
    def serialize_paths(self, path: Path) -> str:
        return str(path)
