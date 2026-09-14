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

    def forget_missing(self) -> None:
        """Keeps the favorites still standing on the disk.

        A star is taken off from the row it marks, so a favorite whose file has gone leaves with
        the file.
        """
        self.paths = {path for path in self.paths if path.exists()}

    @field_serializer("paths")
    def serialize_paths(self, paths: Set[Path]) -> List[str]:
        return [str(path) for path in paths]
