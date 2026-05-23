from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.paths import APPLICATION_CONFIG_PATH
from sampletones.data import Metadata
from sampletones.logger import logger
from sampletones.types.path import Pathlike
from sampletones.utils import load_yaml, save_yaml, to_path

from .audio import AudioConfig
from .favorites import Favorites
from .gui import GUIState
from .paths import LastPaths
from .window import WindowState


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
    gui: GUIState = Field(
        default_factory=GUIState,
        description="The state of the graphical user interface.",
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
