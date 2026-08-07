from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DANGER_BUTTON,
    TAG_GLOBAL_THEME_PANEL_EMPHASIS,
    TAG_GLOBAL_THEME_PRIMARY_BUTTON,
)
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_BUTTON_ACTION,
    TAG_MAIN_CONVERTER_GROUP,
    TAG_MAIN_CONVERTER_GROUP_CONVERT,
    TAG_MAIN_CONVERTER_GROUP_SUMMARY,
    TAG_MAIN_CONVERTER_PANEL,
    TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
    TAG_MAIN_CONVERTER_PROGRESS,
    TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
    TAG_MAIN_CONVERTER_TEXT_STATUS,
    TAG_MAIN_CONVERTER_TEXT_SUMMARY_HINT,
    TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
    TAG_MAIN_CONVERTER_WINDOW_SUMMARY,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_set_item_callback,
    dpg_set_value,
)
from sampletones_application.utils.gui.tooltip import attach_disabled_tooltip
from sampletones_application.view_model.main.converter import (
    ConverterAction,
    ConverterViewModel,
)
from sampletones_shared.types.callback import VoidCallback


class GUIConverterPanel(GUIPanel):
    def __init__(
        self,
        *,
        layout: ConverterLayout,
        path_colors: PathColors,
        initial_collapsed: bool = False,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None
        self._status_bar = status_bar
        self._action_button: Optional[GUIButton] = None
        self._theme_convert: Optional[Theme] = None
        self._theme_cancel: Optional[Theme] = None

        self.on_convert_requested: Optional[VoidCallback] = None
        self.on_cancel_requested: Optional[VoidCallback] = None

        self._layout = layout
        self._path_colors = path_colors
        self._msg_path = language_manager["global.status.message.path"]
        self._msg_status_convert = language_manager["main.converter.message.status_convert"]
        self._status_action_message = self._msg_status_convert

        super().__init__(
            tag=TAG_MAIN_CONVERTER_PANEL,
            height=layout.height,
        )
        self._enable_vertical_collapse(initial_collapsed=initial_collapsed)

    def create_panel(self, parent: str) -> None:
        with self._collapsible_card(
            parent,
            self._language_manager["main.converter.label.section"],
            glyph=self._glyphs.headers.converter,
            width=self.width,
            card_theme=TAG_GLOBAL_THEME_PANEL_EMPHASIS,
        ):
            self._create_action_button()
            dpg.add_separator()
            self._create_summary()
            self._create_conversion_status()

    def is_visible(self) -> bool:
        return bool(dpg.get_item_configuration(self.tag)["show"])

    def update_view(self, view_model: ConverterViewModel) -> None:
        self._update_visibility(view_model)
        self._update_status(view_model)
        self._update_paths(view_model)
        self._update_controls(view_model)

    def _update_visibility(self, view_model: ConverterViewModel) -> None:
        has_input = view_model.input_path is not None
        dpg.configure_item(TAG_MAIN_CONVERTER_GROUP, show=view_model.subpanel_visible)
        dpg_configure_item(TAG_MAIN_CONVERTER_WINDOW_SUMMARY, show=not view_model.subpanel_visible)
        dpg_configure_item(TAG_MAIN_CONVERTER_TEXT_SUMMARY_HINT, show=not has_input)
        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP_SUMMARY, show=has_input)

    def _update_status(self, view_model: ConverterViewModel) -> None:
        dpg_set_value(TAG_MAIN_CONVERTER_TEXT_STATUS, view_model.status_text)
        dpg_set_value(TAG_MAIN_CONVERTER_PROGRESS, view_model.progress)
        dpg_configure_item(TAG_MAIN_CONVERTER_PROGRESS, overlay=view_model.progress_overlay)

    def _update_paths(self, view_model: ConverterViewModel) -> None:
        if self.input_path_text is not None and view_model.input_path is not None:
            self.input_path_text.set_path(view_model.input_path)
        if self.output_path_text is not None and view_model.output_path is not None:
            self.output_path_text.set_path(view_model.output_path)

    def _update_controls(self, view_model: ConverterViewModel) -> None:
        match view_model.primary_action:
            case ConverterAction.CANCEL:
                callback: VoidCallback = self._on_cancel_clicked
                theme = self._theme_cancel
                self._status_action_message = self._language_manager["main.converter.message.status_cancel"]
            case ConverterAction.CONVERT:
                callback = self._on_convert_clicked
                theme = self._theme_convert
                self._status_action_message = self._msg_status_convert

        dpg_configure_item(
            TAG_MAIN_CONVERTER_BUTTON_ACTION,
            label=view_model.action_label,
            enabled=view_model.primary_action_enabled,
        )
        dpg_set_item_callback(TAG_MAIN_CONVERTER_BUTTON_ACTION, callback)
        if self._action_button is not None and theme is not None:
            self._action_button.set_theme(theme)
        dpg_configure_item(
            TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
            show=view_model.other_operation_active and view_model.primary_action == ConverterAction.CONVERT,
        )

    def _create_action_button(self) -> None:
        self._theme_convert = ThemeRegistry.get(TAG_GLOBAL_THEME_PRIMARY_BUTTON)
        self._theme_cancel = ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON)
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_CONVERT):
            self._action_button = GUIButton(
                label=self._language_manager["main.converter.label.convert_sample_button"],
                tag=TAG_MAIN_CONVERTER_BUTTON_ACTION,
                width=self._layout.width,
                height=self._layout.button_height,
                font=Font.BOLD_LARGE,
                enabled=False,
                callback=self._on_convert_clicked,
                theme=self._theme_convert,
            )
        attach_disabled_tooltip(
            TAG_MAIN_CONVERTER_GROUP_CONVERT,
            self._language_manager["global.dialog.message.operation_in_progress"],
            tag=TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
        )
        self._status_bar.bind_to_item(
            TAG_MAIN_CONVERTER_BUTTON_ACTION,
            self._action_status_message,
        )

    def _action_status_message(self, *args: Any, **kwargs: Any) -> str:
        return self._status_action_message

    def _create_summary(self) -> None:
        with dpg.child_window(
            tag=TAG_MAIN_CONVERTER_WINDOW_SUMMARY,
            width=-1,
            height=-1,
            border=False,
        ):
            hint = dpg.add_text(
                self._language_manager["main.converter.message.status_empty_hint"],
                tag=TAG_MAIN_CONVERTER_TEXT_SUMMARY_HINT,
            )
            FontRegistry.bind_to_item(hint, Font.REGULAR_SMALL)
            with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_SUMMARY, show=False):
                self.input_path_text = GUIPathText(
                    path=None,
                    prefix=self._language_manager["main.converter.message.status_input_label"],
                    tag=TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
                    parent=TAG_MAIN_CONVERTER_GROUP_SUMMARY,
                    color=self._path_colors.default,
                    hover_color=self._path_colors.hover,
                    status_message=self._msg_path,
                    font=Font.REGULAR_SMALL,
                    status_bar=self._status_bar,
                )
                self.output_path_text = GUIPathText(
                    path=None,
                    prefix=self._language_manager["main.converter.message.status_output_label"],
                    tag=TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
                    parent=TAG_MAIN_CONVERTER_GROUP_SUMMARY,
                    color=self._path_colors.default,
                    hover_color=self._path_colors.hover,
                    status_message=self._msg_path,
                    font=Font.REGULAR_SMALL,
                    status_bar=self._status_bar,
                )

    def _create_conversion_status(self) -> None:
        with dpg.group(
            tag=TAG_MAIN_CONVERTER_GROUP,
            show=False,
        ):
            dpg.add_text(
                self._language_manager["main.converter.message.status_waiting"],
                tag=TAG_MAIN_CONVERTER_TEXT_STATUS,
                parent=TAG_MAIN_CONVERTER_GROUP,
            )
            FontRegistry.bind_to_item(
                TAG_MAIN_CONVERTER_TEXT_STATUS,
                Font.MONO_SMALL,
            )
            dpg.add_progress_bar(
                tag=TAG_MAIN_CONVERTER_PROGRESS,
                parent=TAG_MAIN_CONVERTER_GROUP,
                default_value=0.0,
                width=-1,
                overlay="0%",
            )
            FontRegistry.bind_to_item(TAG_MAIN_CONVERTER_PROGRESS, Font.MONO)

    def _on_convert_clicked(self) -> None:
        self.call(self.on_convert_requested)

    def _on_cancel_clicked(self) -> None:
        self.call(self.on_cancel_requested)
