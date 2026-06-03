from typing import Final

from pydantic import BaseModel, Field

_DEFAULT_WIDTH: Final = 1280
_DEFAULT_HEIGHT: Final = 800
_DEFAULT_POSITION_X: Final = 200
_DEFAULT_POSITION_Y: Final = 200
_DEFAULT_FULLSCREEN: Final = False


class WindowState(BaseModel):
    width: int = Field(default=_DEFAULT_WIDTH, description="The width of the main application window.")
    height: int = Field(default=_DEFAULT_HEIGHT, description="The height of the main application window.")
    x: int = Field(default=_DEFAULT_POSITION_X, description="The x-coordinate of the main application window.")
    y: int = Field(default=_DEFAULT_POSITION_Y, description="The y-coordinate of the main application window.")
    fullscreen: bool = Field(
        default=_DEFAULT_FULLSCREEN,
        description="Whether the main application window is fullscreen.",
    )
