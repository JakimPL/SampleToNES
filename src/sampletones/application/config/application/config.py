from pathlib import Path
from typing import Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.paths import APPLICATION_CONFIG_PATH
from sampletones.utils import load_yaml, save_yaml, to_path

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

    @classmethod
    def default(cls) -> "ApplicationConfig":
        if not APPLICATION_CONFIG_PATH.exists():
            return cls()

        return cls.load(APPLICATION_CONFIG_PATH)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "ApplicationConfig":
        path = to_path(path)
        config_dict = load_yaml(path)
        return cls(**config_dict)

    def save(self, path: Union[str, Path]) -> None:
        path = to_path(path)
        config_dict = self.model_dump()
        save_yaml(path, config_dict)
