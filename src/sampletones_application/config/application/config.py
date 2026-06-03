from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.config.application.audio import AudioConfig
from sampletones_application.config.application.favorites import Favorites
from sampletones_application.config.application.paths import LastPaths
from sampletones_application.config.application.window import WindowState
from sampletones_core.data import Metadata


class ApplicationConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: Metadata = Field(
        default_factory=Metadata,
        description="Metadata about the application configuration.",
    )
    audio: AudioConfig = Field(
        default_factory=AudioConfig,
        description="The audio configuration settings.",
    )
    window: WindowState = Field(
        default_factory=WindowState,
        description="The state of the main application window.",
    )
    last_paths: LastPaths = Field(
        default_factory=LastPaths,
        description="The last used file system paths.",
    )
    favorites: Favorites = Field(
        default_factory=Favorites,
        description="The user's favorite files and recent files.",
    )
