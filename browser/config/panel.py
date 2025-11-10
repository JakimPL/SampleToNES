from pathlib import Path
from typing import Any, Callable, Optional, Union

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.elements.panel import GUIPanel
from browser.elements.path import GUIPathText
from browser.utils import file_dialog_handler
from constants.browser import (
    DIM_DIALOG_FILE_HEIGHT,
    DIM_DIALOG_FILE_WIDTH,
    DIM_PANEL_CONFIG_HEIGHT,
    DIM_PANEL_CONFIG_WIDTH,
    LBL_BUTTON_SELECT_LIBRARY_DIRECTORY,
    LBL_CHECKBOX_NORMALIZE_AUDIO,
    LBL_CHECKBOX_QUANTIZE_AUDIO,
    LBL_INPUT_CHANGE_RATE,
    LBL_INPUT_MAX_WORKERS,
    LBL_INPUT_SAMPLE_RATE,
    LBL_SECTION_GENERAL_SETTINGS,
    LBL_SECTION_LIBRARY_DIRECTORY,
    LBL_SECTION_LIBRARY_SETTINGS,
    RNG_CONFIG_MIN_WORKERS,
    TAG_CONFIG_CHANGE_RATE,
    TAG_CONFIG_MAX_WORKERS,
    TAG_CONFIG_NORMALIZE,
    TAG_CONFIG_PANEL,
    TAG_CONFIG_PANEL_GROUP,
    TAG_CONFIG_QUANTIZE,
    TAG_CONFIG_SAMPLE_RATE,
    TAG_LIBRARY_DIRECTORY_DISPLAY,
    TITLE_DIALOG_SELECT_LIBRARY_DIRECTORY,
)
from constants.general import (
    CHANGE_RATE,
    MAX_CHANGE_RATE,
    MAX_SAMPLE_RATE,
    MAX_WORKERS,
    MIN_CHANGE_RATE,
    MIN_SAMPLE_RATE,
    NORMALIZE,
    QUANTIZE,
    SAMPLE_RATE,
)
from library.key import LibraryKey
from utils.serialization import SerializedData


class GUIConfigPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

        self._on_update_library_directory: Optional[Callable[[], None]] = None
        self.library_path_text: Optional[GUIPathText] = None

        super().__init__(
            tag=TAG_CONFIG_PANEL,
            width=DIM_PANEL_CONFIG_WIDTH,
            height=DIM_PANEL_CONFIG_HEIGHT,
            parent=TAG_CONFIG_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
        ):
            dpg.add_text(LBL_SECTION_GENERAL_SETTINGS)
            dpg.add_separator()

            dpg.add_checkbox(label=LBL_CHECKBOX_NORMALIZE_AUDIO, default_value=NORMALIZE, tag=TAG_CONFIG_NORMALIZE)
            dpg.add_checkbox(label=LBL_CHECKBOX_QUANTIZE_AUDIO, default_value=QUANTIZE, tag=TAG_CONFIG_QUANTIZE)
            dpg.add_input_int(
                label=LBL_INPUT_MAX_WORKERS,
                default_value=MAX_WORKERS,
                tag=TAG_CONFIG_MAX_WORKERS,
                min_value=RNG_CONFIG_MIN_WORKERS,
            )

            dpg.add_separator()
            dpg.add_text(LBL_SECTION_LIBRARY_DIRECTORY)
            dpg.add_button(
                label=LBL_BUTTON_SELECT_LIBRARY_DIRECTORY,
                width=-1,
                callback=self._select_library_directory_dialog,
            )

            library_directory = self.config_manager.get_library_directory()
            self.library_path_text = GUIPathText(
                tag=TAG_LIBRARY_DIRECTORY_DISPLAY,
                path=library_directory,
                parent=self.tag,
            )

            dpg.add_separator()
            dpg.add_text(LBL_SECTION_LIBRARY_SETTINGS)
            dpg.add_separator()

            dpg.add_input_int(
                label=LBL_INPUT_SAMPLE_RATE,
                default_value=SAMPLE_RATE,
                tag=TAG_CONFIG_SAMPLE_RATE,
                min_value=MIN_SAMPLE_RATE,
                max_value=MAX_SAMPLE_RATE,
            )
            dpg.add_input_int(
                label=LBL_INPUT_CHANGE_RATE,
                default_value=CHANGE_RATE,
                tag=TAG_CONFIG_CHANGE_RATE,
                min_value=MIN_CHANGE_RATE,
                max_value=MAX_CHANGE_RATE,
            )

        self._register_callbacks()

    def _register_callbacks(self) -> None:
        for tag in self.config_manager.config_parameters["config"].keys():
            dpg.set_item_callback(tag, self._on_parameter_change)

    def _on_parameter_change(self, sender: Any, app_data: Any) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _get_all_gui_values(self) -> SerializedData:
        gui_values = {}
        for tag in self.config_manager.config_parameters["config"].keys():
            gui_values[tag] = self._clamp_value(tag)

        return gui_values

    def _clamp_value(self, tag: str) -> Union[int, float, bool, str]:
        value = dpg.get_value(tag)
        cfg = dpg.get_item_configuration(tag)

        min_v = cfg.get("min_value")
        max_v = cfg.get("max_value")
        if min_v is not None and isinstance(value, (int, float)):
            if value < min_v:
                value = min_v
        if max_v is not None and isinstance(value, (int, float)):
            if value > max_v:
                value = max_v

        return value

    def _select_library_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_SELECT_LIBRARY_DIRECTORY,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._select_library_directory,
            directory_selector=True,
        ):
            pass

    @file_dialog_handler
    def _select_library_directory(self, filepath: Path) -> None:
        self.change_library_directory(filepath)

    def change_library_directory(self, directory_path: Path) -> None:
        self.config_manager.library_directory = directory_path
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

        if self.library_path_text:
            self.library_path_text.set_path(directory_path)

        if self._on_update_library_directory is not None:
            self._on_update_library_directory()

    def apply_library_config(self, library_key: LibraryKey) -> None:
        gui_updates = self.config_manager.apply_library_config(library_key)
        for tag, value in gui_updates.items():
            dpg.set_value(tag, value)

    def update_gui_from_config(self) -> None:
        if not self.config_manager.config:
            return

        config = self.config_manager.config
        for tag, info in self.config_manager.config_parameters["config"].items():
            section_name = info["section"]
            section = getattr(config, section_name)
            if hasattr(section, tag):
                dpg.set_value(tag, getattr(section, tag))

        library_directory = Path(config.general.library_directory)
        if self.library_path_text:
            self.library_path_text.set_path(library_directory)

    def set_callbacks(self, on_update_library_directory: Optional[Callable[[], None]] = None) -> None:
        if on_update_library_directory is not None:
            self._on_update_library_directory = on_update_library_directory
