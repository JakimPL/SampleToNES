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
