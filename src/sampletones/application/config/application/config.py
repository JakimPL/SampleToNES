from pydantic import BaseModel, ConfigDict, Field

from .gui import GUIState
from .paths import LastPaths
from .window import WindowState


class ApplicationConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    window_state: WindowState = Field(
        default_factory=WindowState,
        description="The state of the main application window.",
    )
    gui_state: GUIState = Field(
        default_factory=GUIState,
        description="The state of the graphical user interface.",
    )
    last_paths: LastPaths = Field(
        default_factory=LastPaths,
        description="The last used file system paths.",
    )
