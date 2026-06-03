from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.config.application.audio import AudioConfig
from sampletones_application.config.application.favorites import Favorites
from sampletones_application.config.application.paths import LastPaths
from sampletones_application.config.application.state import ApplicationState
from sampletones_application.config.application.window import WindowState
from sampletones_application.paths import APPLICATION_CONFIG_PATH
from sampletones_core.data import Metadata
from sampletones_shared.logger import logger
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml, save_yaml
from sampletones_shared.utils.system.paths import to_path


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
    state: ApplicationState = Field(
        default_factory=ApplicationState,
        description="Auto-managed session state (current tab, reconstruction, autoplay).",
    )
    last_paths: LastPaths = Field(
        default_factory=LastPaths,
        description="The last used file system paths.",
    )
    favorites: Favorites = Field(
        default_factory=Favorites,
        description="The user's favorite files and recent files.",
    )

    @classmethod
    def default(cls) -> ApplicationConfig:
        if not APPLICATION_CONFIG_PATH.exists():
            logger.warning(
                f"Application config file '{APPLICATION_CONFIG_PATH}' does not exist. Loading default configuration."
            )
            return cls()

        return cls.load(APPLICATION_CONFIG_PATH)

    @classmethod
    def load(cls, path: Pathlike) -> ApplicationConfig:
        path = to_path(path)
        config_dict = load_yaml(path)
        if not config_dict:
            logger.warning(f"Application config file '{path}' is empty or invalid. Loading default configuration.")
            return cls()

        if not isinstance(config_dict, dict):
            raise TypeError(f"Expected config file to contain a dict, got {type(config_dict)}")

        return cls(**config_dict)

    def save(self, path: Pathlike) -> None:
        path = to_path(path)
        config_dict = self.model_dump()
        save_yaml(path, config_dict)
