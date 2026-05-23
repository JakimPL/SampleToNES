from pathlib import Path
from typing import Optional, Set

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager, CurrentDevice
from sampletones.constants.audio import BufferSize
from sampletones.constants.paths import APPLICATION_CONFIG_PATH
from sampletones.logger import logger
from sampletones.utils import get_directory

from ...constants.general import TAG_TABS
from .config import ApplicationConfig


class ApplicationConfigManager:
    def __init__(self) -> None:
        self.config: ApplicationConfig = self.load_config()

    def load_config(self) -> ApplicationConfig:
        return ApplicationConfig.default()

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

    def load_window_state(self) -> None:
        window_x, window_y = dpg.get_viewport_pos()
        if not self.config.window.fullscreen:
            self.config.window.x = int(window_x)
            self.config.window.y = int(window_y)
            self.config.window.width = dpg.get_viewport_width()
            self.config.window.height = dpg.get_viewport_height()

    def save_current_tab(self) -> None:
        current_tab = dpg.get_value(TAG_TABS)
        current_tab = dpg.get_item_alias(current_tab)
        self.config.gui.current_tab = current_tab

    def toggle_show_advanced_settings(self) -> bool:
        self.config.gui.advanced_settings = not self.config.gui.advanced_settings
        return self.config.gui.advanced_settings

    def toggle_autoplay(self) -> bool:
        self.config.gui.autoplay = not self.config.gui.autoplay
        return self.config.gui.autoplay

    def toggle_favorite(self, path: Path) -> None:
        self.config.favorites.toggle_favorite(path)

    def load_current_tab(self) -> str:
        return self.config.gui.current_tab

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
        self.config.gui.current_reconstruction = path

    def set_current_audio_device(self, audio_device_manager: AudioDeviceManager) -> None:
        self.config.audio.set_audio_settings(audio_device_manager)

    def save_config(self) -> None:
        self.load_window_state()
        self.save_current_tab()

        try:
            APPLICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.config.save(APPLICATION_CONFIG_PATH)
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
        return self.config.gui.current_tab

    @property
    def current_reconstruction(self) -> Optional[Path]:
        return self.config.gui.current_reconstruction

    @property
    def current_audio_device(self) -> CurrentDevice:
        return self.config.audio.current_device

    @property
    def current_buffer_size(self) -> BufferSize:
        return self.config.audio.buffer_size

    @property
    def advanced_settings(self) -> bool:
        return self.config.gui.advanced_settings

    @property
    def autoplay(self) -> bool:
        return self.config.gui.autoplay

    @property
    def favorites(self) -> Set[Path]:
        return self.config.favorites.paths
