from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    GlobalMessageElements,
    StatusElements,
)
from sampletones_application.categories.elements.main import ConverterElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.main import (
    TAG_MAIN_CONVERTER_BUTTON_CANCEL,
    TAG_MAIN_CONVERTER_BUTTON_CONVERT,
    TAG_MAIN_CONVERTER_BUTTON_LOAD,
    TAG_MAIN_CONVERTER_GROUP,
    TAG_MAIN_CONVERTER_GROUP_CONVERT,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
    TAG_MAIN_CONVERTER_PROGRESS,
    TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
    TAG_MAIN_CONVERTER_TEXT_STATUS,
    TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
    TAG_MAIN_PANEL,
)
from sampletones_application.layout.general import PathColors
from sampletones_application.layout.main import ConverterLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_set_item_callback,
    dpg_set_value,
)
from sampletones_application.utils.gui.tooltip import attach_disabled_tooltip
from sampletones_application.view_model.main.converter import ConverterViewModel
from sampletones_shared.types.callback import VoidCallback


class GUIConverterPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: ConverterLayout,
        path_colors: PathColors,
        language_manager: LanguageManager,
    ) -> None:
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        self.on_convert_requested: Optional[VoidCallback] = None
        self.on_cancel_requested: Optional[VoidCallback] = None
        self.on_close_requested: Optional[VoidCallback] = None
        self.on_load_requested: Optional[VoidCallback] = None

        self._layout = layout
        self._path_colors = path_colors
        self._msg_path = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.PATH,
        ]
        self._lbl_section = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.SECTION,
        ]
        self._lbl_cancel_button = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.CANCEL_BUTTON,
        ]
        self._lbl_load_button = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.LOAD_BUTTON,
        ]
        self._lbl_convert_button = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.CONVERT_SAMPLE_BUTTON,
        ]
        self._lbl_close_button = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.CLOSE_BUTTON,
        ]
        self._lbl_convert_directory_button = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.LABEL,
            ConverterElements.CONVERT_DIRECTORY_BUTTON,
        ]
        self._tooltip_convert_disabled = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.OPERATION_IN_PROGRESS,
        ]
        self._msg_input = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_INPUT_LABEL,
        ]
        self._msg_output = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_OUTPUT_LABEL,
        ]
        self._msg_waiting = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_WAITING,
        ]

        super().__init__(
            tag=TAG_MAIN_CONVERTER_PANEL,
            parent=TAG_MAIN_PANEL,
            height=layout.height,
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

    def update_view(self, view_model: ConverterViewModel) -> None:
        dpg.configure_item(TAG_MAIN_CONVERTER_GROUP, show=view_model.subpanel_visible)
        dpg_set_value(TAG_MAIN_CONVERTER_TEXT_STATUS, view_model.status_text)
        dpg_set_value(TAG_MAIN_CONVERTER_PROGRESS, view_model.progress)
        dpg_configure_item(TAG_MAIN_CONVERTER_PROGRESS, overlay=view_model.progress_overlay)

        if self.input_path_text is not None and view_model.input_path is not None:
            self.input_path_text.set_path(view_model.input_path)
        if self.output_path_text is not None and view_model.output_path is not None:
            self.output_path_text.set_path(view_model.output_path)

        _cancel_label = self._lbl_close_button if view_model.is_done else self._lbl_cancel_button
        _base_convert = self._lbl_convert_button if view_model.is_file else self._lbl_convert_directory_button
        _convert_label = (
            f"{_base_convert}: {view_model.input_path.name}" if view_model.input_path is not None else _base_convert
        )
        dpg_configure_item(
            TAG_MAIN_CONVERTER_BUTTON_CONVERT,
            label=_convert_label,
            enabled=view_model.convert_button_enabled,
        )
        dpg_configure_item(
            TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
            show=view_model.other_operation_active,
        )
        dpg_configure_item(
            TAG_MAIN_CONVERTER_BUTTON_LOAD,
            enabled=view_model.load_button_enabled,
        )
        dpg_configure_item(
            TAG_MAIN_CONVERTER_BUTTON_CANCEL,
            label=_cancel_label,
        )

        if view_model.is_done:
            dpg_set_item_callback(
                TAG_MAIN_CONVERTER_BUTTON_CANCEL,
                self._on_close_clicked,
            )
        else:
            dpg_set_item_callback(
                TAG_MAIN_CONVERTER_BUTTON_CANCEL,
                self._on_cancel_clicked,
            )

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_section)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_CONVERT):
            GUIButton(
                label=self._lbl_convert_button,
                tag=TAG_MAIN_CONVERTER_BUTTON_CONVERT,
                width=self._layout.width,
                height=self._layout.button_height,
                font=Font.BOLD_LARGE,
                enabled=False,
                callback=self._on_convert_clicked,
            )
        attach_disabled_tooltip(
            TAG_MAIN_CONVERTER_GROUP_CONVERT,
            self._tooltip_convert_disabled,
            tag=TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
        )

    def _create_paths(self) -> None:
        self.input_path_text = GUIPathText(
            path=None,
            prefix=self._msg_input,
            tag=TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
            parent=TAG_MAIN_CONVERTER_GROUP,
            color=self._path_colors.default,
            hover_color=self._path_colors.hover,
            status_message=self._msg_path,
            font=Font.REGULAR_SMALL,
        )
        self.output_path_text = GUIPathText(
            path=None,
            prefix=self._msg_output,
            tag=TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
            parent=TAG_MAIN_CONVERTER_GROUP,
            color=self._path_colors.default,
            hover_color=self._path_colors.hover,
            status_message=self._msg_path,
            font=Font.REGULAR_SMALL,
        )

    def _create_conversion_status(self) -> None:
        with dpg.group(
            tag=TAG_MAIN_CONVERTER_GROUP,
            parent=self.tag,
            show=False,
        ):
            dpg.add_separator()
            dpg.add_text(
                self._msg_waiting,
                tag=TAG_MAIN_CONVERTER_TEXT_STATUS,
                parent=TAG_MAIN_CONVERTER_GROUP,
            )
            dpg.add_progress_bar(
                tag=TAG_MAIN_CONVERTER_PROGRESS,
                parent=TAG_MAIN_CONVERTER_GROUP,
                default_value=0.0,
                width=-1,
                overlay="0%",
            )
            dpg.add_separator()
            self._add_buttons()

    @table_wrapper(columns=2)
    def _add_buttons(self) -> None:
        GUIButton(
            label=self._lbl_load_button,
            tag=TAG_MAIN_CONVERTER_BUTTON_LOAD,
            width=self._layout.width,
            callback=self._on_load_clicked,
            enabled=False,
        )
        GUIButton(
            label=self._lbl_cancel_button,
            tag=TAG_MAIN_CONVERTER_BUTTON_CANCEL,
            width=self._layout.width,
            callback=self._on_cancel_clicked,
        )

    def _on_convert_clicked(self) -> None:
        self.call(self.on_convert_requested)

    def _on_cancel_clicked(self) -> None:
        self.call(self.on_cancel_requested)

    def _on_close_clicked(self) -> None:
        self.call(self.on_close_requested)

    def _on_load_clicked(self) -> None:
        dpg_configure_item(TAG_MAIN_CONVERTER_BUTTON_LOAD, enabled=False)
        self.call(self.on_load_requested)
