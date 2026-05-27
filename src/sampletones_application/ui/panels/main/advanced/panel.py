from pathlib import Path
from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.config.updates import AdvancedSettingsUpdate
from sampletones_application.constants.general import (
    DIM_DIALOG_HEIGHT_FILE,
    DIM_DIALOG_WIDTH_FILE,
    DIM_INPUT_WIDTH,
    SUF_HANDLER_REGISTRY,
)
from sampletones_application.constants.main import (
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
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.panels.main.advanced.viewmodel import AdvancedSettingsPanelViewModel
from sampletones_application.utils.align import table_wrapper
from sampletones_application.utils.file import file_dialog_handler
from sampletones_application.utils.tooltip import show_tooltip
from sampletones_application.utils.widgets import clamp_widget_value
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


class GUIAdvancedSettingsPanel(GUIPanel):
    def __init__(self, initial_view: AdvancedSettingsPanelViewModel) -> None:
        self.on_advanced_settings_changed: Optional[Callable[[AdvancedSettingsUpdate], None]] = None
        self.on_library_path_memorized: Optional[Callable[[Path], None]] = None
        self.on_update_library_directory: Optional[VoidCallback] = None
        self.on_update_output_directory: Optional[VoidCallback] = None

        self._library_directory: Path = initial_view.library_directory
        self._output_directory: Path = initial_view.output_directory
        self._max_workers: int = initial_view.max_workers

        self._item_handler_tag = f"{TAG_PANEL_MAIN_ADVANCED}{SUF_HANDLER_REGISTRY}"

        self.library_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        super().__init__(
            tag=TAG_PANEL_MAIN_ADVANCED,
            parent=TAG_PANEL_MAIN_SETTINGS,
            height=DIM_PANEL_HEIGHT_MAIN_ADVANCED,
        )

    def create_panel(self) -> None:
        self._setup_handlers()
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

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self._item_handler_tag):
            dpg.add_item_deactivated_handler(callback=self._on_parameter_change)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_parameter_change)
            dpg.add_item_edited_handler(callback=self._on_parameter_change)

    def _on_parameter_change(self, sender: Sender, app_data: Any) -> None:
        advanced_update = AdvancedSettingsUpdate(
            max_workers=int(clamp_widget_value(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS)),
            library_directory=self._library_directory,
            output_directory=self._output_directory,
        )
        self.call(self.on_advanced_settings_changed, advanced_update)

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
            default_value=self._max_workers,
            tag=TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS,
            min_value=VAL_RANGE_MAIN_ADVANCED_MAX_WORKERS,
            width=DIM_INPUT_WIDTH,
        )

        dpg.bind_item_handler_registry(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS, self._item_handler_tag)

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

            self.library_path_text = GUIPathText(
                tag=TAG_PATH_MAIN_ADVANCED_LIBRARY_DIRECTORY_DISPLAY,
                parent=TAG_GROUP_MAIN_ADVANCED_LIBRARY_DIRECTORY,
                path=self._library_directory,
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

            self.output_path_text = GUIPathText(
                tag=TAG_PATH_MAIN_ADVANCED_OUTPUT_DIRECTORY_DISPLAY,
                parent=TAG_GROUP_MAIN_ADVANCED_OUTPUT_DIRECTORY,
                path=self._output_directory,
                font=Font.REGULAR_SMALL,
            )

    def _create_tooltips(self) -> None:
        show_tooltip(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS, LBL_TOOLTIP_MAIN_ADVANCED_MAX_WORKERS)

    def _select_library_directory_dialog(self) -> None:
        with dpg.file_dialog(
            label=TTL_DIALOG_MAIN_ADVANCED_SELECT_LIBRARY_DIRECTORY,
            width=DIM_DIALOG_WIDTH_FILE,
            height=DIM_DIALOG_HEIGHT_FILE,
            callback=self._handle_select_library_directory,
            directory_selector=True,
            default_path=str(self._library_directory),
        ):
            pass

    @file_dialog_handler
    def _handle_select_library_directory(self, filepath: Path) -> None:
        self.change_library_directory(filepath)
        self.call(self.on_library_path_memorized, filepath)

    def change_library_directory(self, directory_path: Path) -> None:
        self._library_directory = directory_path
        advanced_update = AdvancedSettingsUpdate(
            max_workers=int(clamp_widget_value(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS)),
            library_directory=self._library_directory,
            output_directory=self._output_directory,
        )
        self.call(self.on_advanced_settings_changed, advanced_update)

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
            default_path=str(self._output_directory),
        ):
            pass

    @file_dialog_handler
    def _handle_select_output_directory(self, directory_path: Path) -> None:
        self.change_output_directory(directory_path)

    def change_output_directory(self, directory_path: Path) -> None:
        self._output_directory = directory_path
        advanced_update = AdvancedSettingsUpdate(
            max_workers=int(clamp_widget_value(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS)),
            library_directory=self._library_directory,
            output_directory=self._output_directory,
        )
        self.call(self.on_advanced_settings_changed, advanced_update)

        if self.output_path_text is not None:
            self.output_path_text.set_path(directory_path)

        self.call(self.on_update_output_directory)

    def update_view(self, viewmodel: AdvancedSettingsPanelViewModel) -> None:
        self._library_directory = viewmodel.library_directory
        self._output_directory = viewmodel.output_directory
        dpg.set_value(TAG_INPUT_MAIN_ADVANCED_MAX_WORKERS, viewmodel.max_workers)

        if self.output_path_text:
            self.output_path_text.set_path(viewmodel.output_directory)

        if self.library_path_text:
            self.library_path_text.set_path(viewmodel.library_directory)
