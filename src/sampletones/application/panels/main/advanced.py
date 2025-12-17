from pathlib import Path
from typing import Any, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones.constants.general import MAX_WORKERS
from sampletones.library import InstructionLibraryKey
from sampletones.typehints import Sender, SerializedData, VoidCallback
from sampletones.utils import to_path

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import (
    DIM_DIALOG_HEIGHT_FILE,
    DIM_DIALOG_WIDTH_FILE,
    DIM_INPUT_WIDTH,
)
from ...constants.main import (
    DIM_PANEL_HEIGHT_MAIN_ADVANCED,
    LBL_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
    LBL_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY,
    LBL_INPUT_MAIN_ADVANCED_MAX_WORKERS,
    LBL_SECTION_MAIN_ADVANCED,
    LBL_TOOLTIP_MAIN_ADVANCED_MAX_WORKERS,
    TAG_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
    TAG_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY,
    TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY,
    TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY,
    TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS,
    TAG_PANEL_MAIN_ADVANCED,
    TAG_PANEL_MAIN_SETTINGS,
    TAG_PATH_MAIN_ADVANCED_LIBRARY_DIRECTORY_DISPLAY,
    TAG_PATH_MAIN_ADVANCED_OUTPUT_DIRECTORY_DISPLAY,
    TTL_DIALOG_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
    TTL_DIALOG_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY,
    VAL_RANGE_MAIN_ADVANCED_MAX_WORKERS,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel
from ...elements.path import GUIPathText
from ...utils.align import table_wrapper
from ...utils.dpg import dpg_set_value
from ...utils.file import file_dialog_handler
from ...utils.tooltip import show_tooltip


class GUIAdvancedSettingsPanel(GUIPanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
    ):
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager

        self.on_update_library_directory: Optional[VoidCallback] = None
        self.on_update_output_directory: Optional[VoidCallback] = None

        self.library_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        super().__init__(
            tag=TAG_PANEL_MAIN_ADVANCED,
            parent=TAG_PANEL_MAIN_SETTINGS,
            height=DIM_PANEL_HEIGHT_MAIN_ADVANCED,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=True,
        ):
            self._create_section_text()
            self._create_workers_settings()
            self._create_path_settings()
            self._create_tooltips()

        self._register_callbacks()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_ADVANCED)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    @table_wrapper(columns=2, height=-1)
    def _create_path_settings(self) -> None:
        self._create_library_directory_selection()
        self._create_output_directory_selection()

    def _create_workers_settings(self) -> None:
        dpg.add_separator()
        dpg.add_input_int(
            label=LBL_INPUT_MAIN_ADVANCED_MAX_WORKERS,
            default_value=MAX_WORKERS,
            tag=TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS,
            min_value=VAL_RANGE_MAIN_ADVANCED_MAX_WORKERS,
            width=DIM_INPUT_WIDTH,
        )

    def _create_library_directory_selection(self) -> None:
        with dpg.child_window(
            tag=TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY,
            width=-1,
            height=-1,
            border=False,
        ):
            GUIButton(
                tag=TAG_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
                parent=TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY,
                label=LBL_BUTTON_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
                width=-1,
                callback=self._select_library_directory_dialog,
            )

            library_directory = self.config_manager.get_library_directory()
            self.library_path_text = GUIPathText(
                tag=TAG_PATH_MAIN_ADVANCED_LIBRARY_DIRECTORY_DISPLAY,
                parent=TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY,
                path=library_directory,
                font=Font.REGULAR_SMALL,
            )

    def _create_output_directory_selection(self) -> None:
        with dpg.child_window(
            tag=TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY,
            width=-1,
            height=-1,
            border=False,
        ):
            GUIButton(
                tag=TAG_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY,
                label=LBL_BUTTON_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY,
                parent=TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY,
                width=-1,
                callback=self._select_output_directory_dialog,
            )

            output_directory = self.config_manager.get_output_directory()
            self.output_path_text = GUIPathText(
                tag=TAG_PATH_MAIN_ADVANCED_OUTPUT_DIRECTORY_DISPLAY,
                parent=TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY,
                path=output_directory,
                font=Font.REGULAR_SMALL,
            )

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS, LBL_TOOLTIP_MAIN_ADVANCED_MAX_WORKERS)

    def _register_callbacks(self) -> None:
        for tag in self.config_manager.config_parameters["advanced"].keys():
            dpg.set_item_callback(tag, self._on_parameter_change)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

    def _get_all_gui_values(self) -> SerializedData:
        gui_values = {}
        for tag in self.config_manager.config_parameters["advanced"].keys():
            gui_values[tag] = self._clamp_value(tag)

        return gui_values

    def _clamp_value(self, tag: str) -> Union[int, float, bool, str]:
        value: Union[int, float, bool, str] = dpg.get_value(tag)
        item_config = dpg.get_item_configuration(tag)

        min_v = item_config.get("min_value")
        max_v = item_config.get("max_value")

        if isinstance(value, (int, float)):
            if min_v is not None:
                value = max(value, min_v)
            if max_v is not None:
                value = min(value, max_v)

        return value

    def _select_library_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TTL_DIALOG_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_select_library_directory,
            directory_selector=True,
            default_path=str(self.application_config_manager.get_library_path()),
        ):
            pass

    @file_dialog_handler
    def _handle_select_library_directory(self, filepath: Path) -> None:
        self.change_library_directory(filepath)
        self.application_config_manager.set_library_path(filepath)

    def change_library_directory(self, directory_path: Path) -> None:
        self.config_manager.library_directory = directory_path
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

        if self.library_path_text:
            self.library_path_text.set_path(directory_path)

        self.call(self.on_update_library_directory)

    def _select_output_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TTL_DIALOG_MAIN_ADVANCED_SELECT_OUTPUT_DIRECTORY,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_select_output_directory,
            directory_selector=True,
            default_path=str(self.config_manager.get_output_directory()),
        ):
            pass

    @file_dialog_handler
    def _handle_select_output_directory(self, directory_path: Path) -> None:
        self.change_output_directory(directory_path)

    def change_output_directory(self, directory_path: Path) -> None:
        self.config_manager.output_directory = directory_path
        gui_values = self._get_all_gui_values()
        self.config_manager.update_config_from_gui_values(gui_values)

        if self.output_path_text is not None:
            self.output_path_text.set_path(directory_path)

        self.call(self.on_update_output_directory)

    def apply_library_config(self, library_key: InstructionLibraryKey) -> None:
        gui_updates = self.config_manager.apply_library_config(library_key)
        for tag, value in gui_updates.items():
            dpg_set_value(tag, value)

    def update_gui_from_config(self) -> None:
        if not self.config_manager.config:
            return

        config = self.config_manager.config
        for tag, info in self.config_manager.config_parameters["config"].items():
            section_name = info["section"]
            section = getattr(config, section_name)
            if hasattr(section, tag):
                dpg.set_value(tag, getattr(section, tag))

        output_directory = to_path(config.general.output_directory)
        if self.output_path_text:
            self.output_path_text.set_path(output_directory)

        library_directory = to_path(config.general.library_directory)
        if self.library_path_text:
            self.library_path_text.set_path(library_directory)
