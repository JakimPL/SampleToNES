from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    VAL_GLOBAL_PROGRESS_START,
)
from sampletones_application.constants.main import (
    DIM_BUTTON_HEIGHT_MAIN_CONVERTER,
    DIM_BUTTON_WIDTH_MAIN_CONVERTER,
    DIM_PANEL_HEIGHT_MAIN_CONVERTER,
    LBL_BUTTON_MAIN_CONVERTER_CANCEL,
    LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE,
    LBL_BUTTON_MAIN_CONVERTER_LOAD,
    LBL_SECTION_MAIN_CONVERTER,
    MSG_MAIN_CONVERTER_INPUT,
    MSG_MAIN_CONVERTER_OUTPUT,
    MSG_MAIN_CONVERTER_WAITING,
    TAG_BUTTON_MAIN_CONVERTER_CANCEL,
    TAG_BUTTON_MAIN_CONVERTER_CONVERT,
    TAG_BUTTON_MAIN_CONVERTER_LOAD,
    TAG_GROUP_MAIN_CONVERTER,
    TAG_PANEL_MAIN,
    TAG_PANEL_MAIN_CONVERTER,
    TAG_PATH_MAIN_CONVERTER_INPUT_PATH,
    TAG_PROGRESS_MAIN_CONVERTER,
    TAG_TEXT_MAIN_CONVERTER_OUTPUT_PATH,
    TAG_TEXT_MAIN_CONVERTER_STATUS,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.utils.align import table_wrapper
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_item_callback, dpg_set_value
from sampletones_application.view_model.converter.converter import ConverterViewModel
from sampletones_shared.types.callback import VoidCallback


class GUIConverterPanel(GUIPanel):
    def __init__(self) -> None:
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        self.on_convert_requested: Optional[VoidCallback] = None
        self.on_cancel_requested: Optional[VoidCallback] = None
        self.on_close_requested: Optional[VoidCallback] = None
        self.on_load_requested: Optional[VoidCallback] = None

        super().__init__(
            tag=TAG_PANEL_MAIN_CONVERTER,
            parent=TAG_PANEL_MAIN,
            height=DIM_PANEL_HEIGHT_MAIN_CONVERTER,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=False,
        ):
            self._create_section_text()
            self._create_export_button()
            self._create_paths()
            self._create_conversion_status()

    def update_view(self, viewmodel: ConverterViewModel) -> None:
        dpg.configure_item(TAG_GROUP_MAIN_CONVERTER, show=viewmodel.subpanel_visible)
        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, viewmodel.status_text)
        dpg_set_value(TAG_PROGRESS_MAIN_CONVERTER, viewmodel.progress)
        dpg_configure_item(TAG_PROGRESS_MAIN_CONVERTER, overlay=viewmodel.progress_overlay)

        if self.input_path_text is not None and viewmodel.input_path is not None:
            self.input_path_text.set_path(viewmodel.input_path)
        if self.output_path_text is not None and viewmodel.output_path is not None:
            self.output_path_text.set_path(viewmodel.output_path)

        dpg_configure_item(
            TAG_BUTTON_MAIN_CONVERTER_CONVERT,
            label=viewmodel.convert_button_label,
            enabled=viewmodel.convert_button_enabled,
        )
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_LOAD, enabled=viewmodel.load_button_enabled)
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_CANCEL, label=viewmodel.cancel_button_label)

        if viewmodel.is_done:
            dpg_set_item_callback(TAG_BUTTON_MAIN_CONVERTER_CANCEL, self._on_close_clicked)
        else:
            dpg_set_item_callback(TAG_BUTTON_MAIN_CONVERTER_CANCEL, self._on_cancel_clicked)

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_CONVERTER)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            label=LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE,
            tag=TAG_BUTTON_MAIN_CONVERTER_CONVERT,
            width=DIM_BUTTON_WIDTH_MAIN_CONVERTER,
            height=DIM_BUTTON_HEIGHT_MAIN_CONVERTER,
            font=Font.BOLD_LARGE,
            enabled=False,
            callback=self._on_convert_clicked,
        )

    def _create_paths(self) -> None:
        self.input_path_text = GUIPathText(
            path=None,
            prefix=MSG_MAIN_CONVERTER_INPUT,
            tag=TAG_PATH_MAIN_CONVERTER_INPUT_PATH,
            parent=TAG_GROUP_MAIN_CONVERTER,
            font=Font.REGULAR_SMALL,
        )
        self.output_path_text = GUIPathText(
            path=None,
            prefix=MSG_MAIN_CONVERTER_OUTPUT,
            tag=TAG_TEXT_MAIN_CONVERTER_OUTPUT_PATH,
            parent=TAG_GROUP_MAIN_CONVERTER,
            font=Font.REGULAR_SMALL,
        )

    def _create_conversion_status(self) -> None:
        with dpg.group(
            tag=TAG_GROUP_MAIN_CONVERTER,
            parent=self.tag,
            show=False,
        ):
            dpg.add_separator()
            dpg.add_text(
                MSG_MAIN_CONVERTER_WAITING,
                tag=TAG_TEXT_MAIN_CONVERTER_STATUS,
                parent=TAG_GROUP_MAIN_CONVERTER,
            )
            dpg.add_progress_bar(
                tag=TAG_PROGRESS_MAIN_CONVERTER,
                parent=TAG_GROUP_MAIN_CONVERTER,
                default_value=VAL_GLOBAL_PROGRESS_START,
                width=-1,
                overlay="0%",
            )
            dpg.add_separator()
            self._add_buttons()

    @table_wrapper(columns=2)
    def _add_buttons(self) -> None:
        GUIButton(
            label=LBL_BUTTON_MAIN_CONVERTER_LOAD,
            tag=TAG_BUTTON_MAIN_CONVERTER_LOAD,
            width=DIM_BUTTON_WIDTH_MAIN_CONVERTER,
            callback=self._on_load_clicked,
            enabled=False,
        )
        GUIButton(
            label=LBL_BUTTON_MAIN_CONVERTER_CANCEL,
            tag=TAG_BUTTON_MAIN_CONVERTER_CANCEL,
            width=DIM_BUTTON_WIDTH_MAIN_CONVERTER,
            callback=self._on_cancel_clicked,
        )

    def _on_convert_clicked(self) -> None:
        self.call(self.on_convert_requested)

    def _on_cancel_clicked(self) -> None:
        self.call(self.on_cancel_requested)

    def _on_close_clicked(self) -> None:
        self.call(self.on_close_requested)

    def _on_load_clicked(self) -> None:
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_LOAD, enabled=False)
        self.call(self.on_load_requested)
