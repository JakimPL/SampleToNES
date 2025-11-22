from pydantic import BaseModel, ConfigDict, Field

from ...constants import (
    DIM_WINDOW_MAIN_HEIGHT,
    DIM_WINDOW_MAIN_WIDTH,
    VAL_WINDOW_FULLSCREEN,
    VAL_WINDOW_POSITION_X,
    VAL_WINDOW_POSITION_Y,
)


class WindowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=DIM_WINDOW_MAIN_WIDTH, description="The width of the main application window.")
    height: int = Field(default=DIM_WINDOW_MAIN_HEIGHT, description="The height of the main application window.")
    x: int = Field(default=VAL_WINDOW_POSITION_X, description="The x-coordinate of the main application window.")
    y: int = Field(default=VAL_WINDOW_POSITION_Y, description="The y-coordinate of the main application window.")
    fullscreen: bool = Field(
        default=VAL_WINDOW_FULLSCREEN,
        description="Whether the main application window is fullscreen.",
    )
