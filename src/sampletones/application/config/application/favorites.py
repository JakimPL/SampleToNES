from pathlib import Path
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Favorites(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    paths: List[Path] = Field(
        default_factory=list,
        description="List of user's favorite file paths.",
    )

    @field_serializer("paths")
    def serialize_paths(self, paths: List[Path]) -> List[str]:
        return [str(path) for path in paths]
