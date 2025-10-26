from pathlib import Path
from typing import Any, Callable, Dict, Optional

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.constants import *
from constants import (
    CHANGE_RATE,
    LIBRARY_DIRECTORY,
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


class ConfigPanelGUI:
    def __init__(self, config_manager: ConfigManager, on_library_directory_changed: Optional[Callable] = None):
        self.config_manager = config_manager
        self.on_library_directory_changed = on_library_directory_changed

    def create_panel(self, parent_tag: str) -> None:
        with dpg.child_window(width=DIM_PANEL_CONFIG_WIDTH, height=DIM_PANEL_CONFIG_HEIGHT, parent=parent_tag):
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
            dpg.add_button(label=LBL_BUTTON_SELECT_LIBRARY_DIR, callback=self._select_library_directory_dialog)
            dpg.add_text(TPL_LIBRARY_DEFAULT_DIR_DISPLAY.format(LIBRARY_DIRECTORY), tag=TAG_LIBRARY_DIRECTORY_DISPLAY)

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

    def create_preview_panel(self, parent_tag: str) -> None:
        with dpg.child_window(parent=parent_tag):
            dpg.add_text(MSG_CONFIG_PREVIEW)
            dpg.add_separator()
            dpg.add_text(MSG_CONFIG_PREVIEW_DEFAULT, tag=TAG_CONFIG_PREVIEW)

    def _register_callbacks(self) -> None:
        for tag in self.config_manager.config_params.keys():
            dpg.set_item_callback(tag, self._on_parameter_change)

    def _on_parameter_change(self, sender: Any, app_data: Any) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _get_all_gui_values(self) -> Dict[str, Any]:
        gui_values = {}
        for tag in self.config_manager.config_params.keys():
            gui_values[tag] = dpg.get_value(tag)
        return gui_values

    def _select_library_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TITLE_DIALOG_SELECT_LIBRARY_DIR,
            width=DIM_DIALOG_FILE_WIDTH,
            height=DIM_DIALOG_FILE_HEIGHT,
            callback=self._select_library_directory,
            directory_selector=True,
        ):
            pass

    def _select_library_directory(self, sender: Any, app_data: Dict[str, Any]) -> None:
        directory_path = list(app_data[KEY_DIALOG_SELECTIONS].values())[IDX_DIALOG_FIRST_SELECTION]
        self.config_manager.set_library_directory(directory_path)
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)
        dpg.set_value(TAG_LIBRARY_DIRECTORY_DISPLAY, TPL_LIBRARY_CUSTOM_DIR_DISPLAY.format(Path(directory_path).name))

        if self.on_library_directory_changed:
            self.on_library_directory_changed()

    def load_config_from_data(self, config_data: Dict[str, Any]) -> None:
        gui_updates = self.config_manager.load_config_from_data(config_data)

        for tag, value in gui_updates.items():
            dpg.set_value(tag, value)

    def apply_library_config(self, library_key: LibraryKey) -> None:
        gui_updates = self.config_manager.apply_library_config(library_key)

        for tag, value in gui_updates.items():
            dpg.set_value(tag, value)
