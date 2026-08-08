from typing import Final

from pydantic import BaseModel, Field

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_shared.display import UNLIMITED_FRAME_RATE

DEFAULT_VSYNC: Final[bool] = True
DEFAULT_MAX_FPS: Final[int] = 60
DEFAULT_BORDERLESS: Final[bool] = False


class DisplayConfig(BaseModel):
    """How the application presents itself: the palette it wears and the pacing it renders at.

    The window's own geometry belongs to the session state, which records where the user left
    the window; these are the preferences a user picks in the display settings and keeps.
    """

    palette: str = Field(
        default=DEFAULT_PALETTE_NAME,
        description="The name of the palette the application draws with.",
    )
    vsync: bool = Field(
        default=DEFAULT_VSYNC,
        description="Whether the render loop waits for the monitor's refresh.",
    )
    max_fps: int = Field(
        default=DEFAULT_MAX_FPS,
        ge=UNLIMITED_FRAME_RATE,
        description="The frame rate the render loop is held to, unlimited at zero.",
    )
    borderless: bool = Field(
        default=DEFAULT_BORDERLESS,
        description="Whether the window is drawn without the system's title bar and frame.",
    )
