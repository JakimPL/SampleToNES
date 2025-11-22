from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ...constants import TAG_TAB_LIBRARY


class GUIState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_tab: str = Field(default=TAG_TAB_LIBRARY, description="The currently selected tab.")
    last_reconstruction: Optional[Path] = Field(
        default=None,
        description="The last used reconstruction path.",
    )
