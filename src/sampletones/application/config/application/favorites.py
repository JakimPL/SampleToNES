from pathlib import Path
from typing import List, Set

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Favorites(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    paths: Set[Path] = Field(
        default_factory=set,
        description="List of user's favorite file paths.",
    )

    def toggle_favorite(self, path: Path) -> None:
        if path in self.paths:
            self.paths.remove(path)
        else:
            self.paths.add(path)

    @field_serializer("paths")
    def serialize_paths(self, paths: Set[Path]) -> List[str]:
        return [str(path) for path in paths]
