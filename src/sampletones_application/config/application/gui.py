from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from sampletones_application.constants.general import TAG_TAB_MAIN


class GUIState(BaseModel):
    current_tab: str = Field(
        default=TAG_TAB_MAIN,
        description="The currently selected tab.",
    )
    current_reconstruction: Optional[Path] = Field(
        default=None,
        description="The currently loaded reconstruction's path.",
    )
    advanced_settings: bool = Field(
        default=False,
        description="If advanced settings are shown in the config panel.",
    )
    autoplay: bool = Field(
        default=True,
        description="If samples should autoplay when clicked.",
    )

    @field_serializer("current_reconstruction")
    def serialize_current_reconstruction(self, value: Optional[Path]) -> Optional[str]:
        if value is None:
            return None

        return str(value)
