from pathlib import Path
from typing import Optional, Set

from sampletones_application.config.application.config import ApplicationConfig
from sampletones_application.config.application.state import ApplicationState
from sampletones_application.paths import APPLICATION_CONFIG_PATH
from sampletones_core.audio import AudioDeviceManager, CurrentDevice
from sampletones_core.constants.audio import BufferSize
from sampletones_shared.logger import logger
from sampletones_shared.utils.serialization import load_yaml, save_yaml
from sampletones_shared.utils.system.paths import get_directory, to_path


class SessionManager:
    def __init__(self) -> None:
        self.config: ApplicationConfig
        self.state: ApplicationState
        self._load()

    def _load(self) -> None:
        if not APPLICATION_CONFIG_PATH.exists():
            logger.warning(
                f"Application config file '{APPLICATION_CONFIG_PATH}' does not exist." " Loading default configuration."
            )
            self.config = ApplicationConfig()
            self.state = ApplicationState()
            return

        raw = load_yaml(to_path(APPLICATION_CONFIG_PATH))
        if not raw or not isinstance(raw, dict):
            logger.warning(
                f"Application config file '{APPLICATION_CONFIG_PATH}' is empty or invalid."
                " Loading default configuration."
            )
            self.config = ApplicationConfig()
            self.state = ApplicationState()
            return

        state_dict = raw.pop("state", None) or {}
        self.config = ApplicationConfig(**raw)
        self.state = ApplicationState(**state_dict)

    def set_window_state(
        self,
        fullscreen: bool,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        self.config.window.fullscreen = fullscreen
        if not fullscreen:
            self.config.window.x = x
            self.config.window.y = y
            self.config.window.width = width
            self.config.window.height = height

    def set_current_tab(self, tab: str) -> None:
        self.state.current_tab = tab

    def toggle_show_advanced_settings(self) -> bool:
        self.state.advanced_settings = not self.state.advanced_settings
        return self.state.advanced_settings

    def toggle_autoplay(self) -> bool:
        self.state.autoplay = not self.state.autoplay
        return self.state.autoplay

    def toggle_favorite(self, path: Path) -> None:
        self.config.favorites.toggle_favorite(path)

    def load_current_tab(self) -> str:
        return self.state.current_tab

    def set_config_path(self, path: Path) -> None:
        self.config.last_paths.config = get_directory(path)

    def get_config_path(self) -> Path:
        return self.config.last_paths.config

    def set_library_path(self, path: Path) -> None:
        self.config.last_paths.library = get_directory(path)

    def get_library_path(self) -> Path:
        return self.config.last_paths.library

    def set_instrument_path(self, path: Path) -> None:
        self.config.last_paths.instrument = get_directory(path)

    def get_instrument_path(self) -> Path:
        return self.config.last_paths.instrument

    def set_reconstruction_path(self, path: Path) -> None:
        self.config.last_paths.reconstruction = get_directory(path)

    def get_reconstruction_path(self) -> Path:
        return self.config.last_paths.reconstruction

    def set_audio_path(self, path: Path) -> None:
        self.config.last_paths.audio = get_directory(path)

    def get_audio_path(self) -> Path:
        return self.config.last_paths.audio

    def set_current_reconstruction(self, path: Optional[Path]) -> None:
        self.state.current_reconstruction = path

    def set_current_audio_device(self, audio_device_manager: AudioDeviceManager) -> None:
        self.config.audio.set_audio_settings(audio_device_manager)

    def save_config(self) -> None:
        try:
            APPLICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = self.config.model_dump()
            data["state"] = self.state.model_dump()
            save_yaml(APPLICATION_CONFIG_PATH, data)
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(
                exception, f"File error while saving application config from {APPLICATION_CONFIG_PATH}"
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save application config to {APPLICATION_CONFIG_PATH}")

    @property
    def fullscreen(self) -> bool:
        return self.config.window.fullscreen

    @property
    def window_x(self) -> int:
        return self.config.window.x

    @property
    def window_y(self) -> int:
        return self.config.window.y

    @property
    def window_width(self) -> int:
        return self.config.window.width

    @property
    def window_height(self) -> int:
        return self.config.window.height

    @property
    def current_tab(self) -> str:
        return self.state.current_tab

    @property
    def current_reconstruction(self) -> Optional[Path]:
        return self.state.current_reconstruction

    @property
    def current_audio_device(self) -> CurrentDevice:
        return self.config.audio.current_device

    @property
    def current_buffer_size(self) -> BufferSize:
        return self.config.audio.buffer_size

    @property
    def advanced_settings(self) -> bool:
        return self.state.advanced_settings

    @property
    def autoplay(self) -> bool:
        return self.state.autoplay

    @property
    def favorites(self) -> Set[Path]:
        return self.config.favorites.paths
