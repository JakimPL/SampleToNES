import dearpygui.dearpygui as dpg

from sampletones.constants.paths import APPLICATION_CONFIG_PATH
from sampletones.utils.logger import logger

from ...constants import TAG_TAB_BAR_MAIN
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
        self.config.window_state.fullscreen = fullscreen
        if not fullscreen:
            self.config.window_state.x = x
            self.config.window_state.y = y
            self.config.window_state.width = width
            self.config.window_state.height = height

    def load_window_state(self) -> None:
        window_x, window_y = dpg.get_viewport_pos()
        if not self.config.window_state.fullscreen:
            self.config.window_state.x = int(window_x)
            self.config.window_state.y = int(window_y)
            self.config.window_state.width = dpg.get_viewport_width()
            self.config.window_state.height = dpg.get_viewport_height()

    def save_current_tab(self) -> None:
        current_tab = dpg.get_value(TAG_TAB_BAR_MAIN)
        current_tab = dpg.get_item_alias(current_tab)
        self.config.gui_state.current_tab = current_tab

    def load_current_tab(self) -> str:
        return self.config.gui_state.current_tab

    def save_config(self) -> None:
        self.load_window_state()
        self.save_current_tab()

        try:
            APPLICATION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.config.save(APPLICATION_CONFIG_PATH)
        except (IOError, OSError, PermissionError, IsADirectoryError) as exception:
            logger.error_with_traceback(
                exception, f"File error while saving application config from {APPLICATION_CONFIG_PATH}"
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save application config to {APPLICATION_CONFIG_PATH}")

    @property
    def is_fullscreen(self) -> bool:
        return self.config.window_state.fullscreen

    @property
    def window_x(self) -> int:
        return self.config.window_state.x

    @property
    def window_y(self) -> int:
        return self.config.window_state.y

    @property
    def window_width(self) -> int:
        return self.config.window_state.width

    @property
    def window_height(self) -> int:
        return self.config.window_state.height
