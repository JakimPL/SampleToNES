from pathlib import Path

from pydantic import BaseModel, Field, field_serializer

from sampletones_core.paths import CONFIG_PATH, LIBRARY_DIRECTORY, PROJECTS_DIRECTORY


class LastPaths(BaseModel):
    library: Path = Field(
        default=LIBRARY_DIRECTORY,
        description="The last used library directory path.",
    )
    reconstruction: Path = Field(
        default=Path.cwd(),
        description="The last used reconstruction directory path.",
    )
    config: Path = Field(
        default=CONFIG_PATH.parent,
        description="The last used configuration file path.",
    )
    instrument: Path = Field(
        default=Path.cwd(),
        description="The last used FTI instrument file path.",
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
        "config",
        "instrument",
        "audio",
        "project",
    )
    def serialize_paths(self, path: Path) -> str:
        return str(path)
