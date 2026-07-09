from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.config.session.application.audio import AudioConfig
from sampletones_application.config.session.application.favorites import Favorites
from sampletones_application.config.session.application.history import HistoryConfig
from sampletones_application.config.session.application.playback import PlaybackConfig
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
    favorites: Favorites = Field(
        default_factory=Favorites,
        description="The user's favorite files and recent files.",
    )
    history: HistoryConfig = Field(
        default_factory=HistoryConfig,
        description="The undo/redo history preferences.",
    )
    playback: PlaybackConfig = Field(
        default_factory=PlaybackConfig,
        description="Playback behaviour preferences.",
    )
