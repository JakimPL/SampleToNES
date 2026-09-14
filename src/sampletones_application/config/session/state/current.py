from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from sampletones_application.categories.hierarchy import Tab


class Current(BaseModel):
    tab: Tab = Field(
        default=Tab.MAIN,
        description="The currently selected tab.",
    )
    reconstruction: Optional[Path] = Field(
        default=None,
        description="The currently loaded reconstruction's path.",
    )
    project: Optional[Path] = Field(
        default=None,
        description="The currently loaded project's path (None for a new, unsaved project).",
    )

    @field_serializer("reconstruction", "project")
    def serialize_paths(self, value: Optional[Path]) -> Optional[str]:
        if value is None:
            return None

        return str(value)

    def forget_missing(self) -> None:
        """Lets go of a reconstruction or project whose file has left the disk since it was open.

        A run restores what the last one had open, so each pointer is held to a file that stands and
        the run opens on what is there to open.
        """
        self.reconstruction = self._standing_file(self.reconstruction)
        self.project = self._standing_file(self.project)

    @staticmethod
    def _standing_file(path: Optional[Path]) -> Optional[Path]:
        if path is None or not path.is_file():
            return None

        return path
