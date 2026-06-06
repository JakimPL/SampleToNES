from pathlib import Path
from typing import Optional

from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml, save_yaml_atomic
from sampletones_shared.utils.system.paths import get_directory, to_path


class ApplicationStateManager:
    def __init__(self) -> None:
        self.state: ApplicationState = self._load()

    def _load(self) -> ApplicationState:
        if not APPLICATION_STATE_PATH.exists():
            return ApplicationState()

        raw = load_yaml(to_path(APPLICATION_STATE_PATH))
        if not raw or not isinstance(raw, dict):
            logger.warning(
                f"Application state file '{APPLICATION_STATE_PATH}' is empty or invalid." " Loading default state."
            )
            return ApplicationState()

        return ApplicationState(**raw)

    def save(self) -> None:
        try:
            APPLICATION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            save_yaml_atomic(APPLICATION_STATE_PATH, self.state.model_dump())
        except (
            IOError,
            IsADirectoryError,
            PermissionError,
            OSError,
        ) as exception:
            logger.error_with_traceback(
                exception,
                f"File error while saving application state to {APPLICATION_STATE_PATH}",
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(
                exception,
                f"Failed to save application state to {APPLICATION_STATE_PATH}",
            )

    def set_window_state(
        self,
        fullscreen: bool,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        self.state.window.fullscreen = fullscreen
        if not fullscreen:
            self.state.window.x = x
            self.state.window.y = y
            self.state.window.width = width
            self.state.window.height = height

    @property
    def fullscreen(self) -> bool:
        return self.state.window.fullscreen

    @property
    def window_x(self) -> int:
        return self.state.window.x

    @property
    def window_y(self) -> int:
        return self.state.window.y

    @property
    def window_width(self) -> int:
        return self.state.window.width

    @property
    def window_height(self) -> int:
        return self.state.window.height

    def set_current_tab(self, tab: str) -> None:
        self.state.current_tab = tab

    def toggle_show_advanced_settings(self) -> bool:
        self.state.advanced_settings = not self.state.advanced_settings
        return self.state.advanced_settings

    def toggle_autoplay(self) -> bool:
        self.state.autoplay = not self.state.autoplay
        return self.state.autoplay

    def load_current_tab(self) -> str:
        return self.state.current_tab

    def set_current_reconstruction(self, path: Optional[Path]) -> None:
        self.state.current_reconstruction = path

    def set_current_project(self, path: Optional[Path]) -> None:
        self.state.current_project = path

    def set_config_path(self, path: Path) -> None:
        self.state.last_paths.config = get_directory(path)

    def get_config_path(self) -> Path:
        return self.state.last_paths.config

    def set_library_path(self, path: Path) -> None:
        self.state.last_paths.library = get_directory(path)

    def get_library_path(self) -> Path:
        return self.state.last_paths.library

    def set_instrument_path(self, path: Path) -> None:
        self.state.last_paths.instrument = get_directory(path)

    def get_instrument_path(self) -> Path:
        return self.state.last_paths.instrument

    def set_reconstruction_path(self, path: Path) -> None:
        self.state.last_paths.reconstruction = get_directory(path)

    def get_reconstruction_path(self) -> Path:
        return self.state.last_paths.reconstruction

    def set_audio_path(self, path: Path) -> None:
        self.state.last_paths.audio = get_directory(path)

    def get_audio_path(self) -> Path:
        return self.state.last_paths.audio

    def set_project_path(self, path: Path) -> None:
        self.state.last_paths.project = get_directory(path)

    def get_project_path(self) -> Path:
        return self.state.last_paths.project

    @property
    def current_tab(self) -> str:
        return self.state.current_tab

    @property
    def current_reconstruction(self) -> Optional[Path]:
        return self.state.current_reconstruction

    @property
    def current_project(self) -> Optional[Path]:
        return self.state.current_project

    @property
    def advanced_settings(self) -> bool:
        return self.state.advanced_settings

    @property
    def autoplay(self) -> bool:
        return self.state.autoplay
