from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from ...constants import TAG_TAB_LIBRARY


class GUIState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_tab: str = Field(default=TAG_TAB_LIBRARY, description="The currently selected tab.")
    current_reconstruction: Optional[Path] = Field(
        default=None,
        description="The currently loaded reconstruction's path.",
    )

    @field_serializer("current_reconstruction")
    def serialize_current_reconstruction(self, value: Optional[Path]) -> Optional[str]:
        if value is None:
            return None

        return str(value)
