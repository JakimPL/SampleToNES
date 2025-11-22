from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sampletones.constants.paths import LIBRARY_DIRECTORY


class LastPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    last_library_path: Path = Field(
        default=LIBRARY_DIRECTORY,
        description="The last used library directory path.",
    )
    last_reconstruction_path: Path = Field(
        default=Path.cwd(),
        description="The last used reconstruction directory path.",
    )

    @field_serializer("last_library_path", "last_reconstruction_path")
    def serialize_paths(self, path: Path) -> str:
        return str(path)
