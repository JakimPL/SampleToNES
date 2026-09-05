from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DANGER_BUTTON,
    TAG_GLOBAL_THEME_PRIMARY_BUTTON,
)
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_BUTTON_ACTION,
    TAG_MAIN_CONVERTER_GROUP_CONVERT,
    TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_item_callback
from sampletones_application.utils.gui.tooltip import attach_disabled_tooltip
from sampletones_application.view_model.main.converter import ConverterAction, ConverterViewModel
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class ConverterActionButton(CallbackMixin):
    """The one button a run is started and stopped from.

    Its label says what the run writes, so the switch above it and the button read as one sentence;
    while a conversion holds resources it cancels instead, and takes the tone that says so.
    """

    def __init__(
        self,
        *,
        layout: ConverterLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._layout = layout
        self._language_manager = language_manager
        self._status_bar = status_bar
        self._button: Optional[GUIButton] = None
        self._theme_convert: Optional[Theme] = None
        self._theme_cancel: Optional[Theme] = None
        self._msg_convert = language_manager["main.converter.message.status_convert"]
        self._msg_cancel = language_manager["main.converter.message.status_cancel"]
        self._status_message = self._msg_convert

        self.on_convert_requested: Optional[VoidCallback] = None
        self.on_cancel_requested: Optional[VoidCallback] = None

    def create(self) -> None:
        """Build the button, opening on the label a converter with nothing gathered carries."""
        self._theme_convert = ThemeRegistry.get(TAG_GLOBAL_THEME_PRIMARY_BUTTON)
        self._theme_cancel = ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON)
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_CONVERT):
            self._button = GUIButton(
                label=self._language_manager["main.converter.label.convert_button"],
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
        self._status_bar.bind_to_item(TAG_MAIN_CONVERTER_BUTTON_ACTION, self._explanation)

    def update_view(self, view_model: ConverterViewModel) -> None:
        """Take up what the run now is: the label it writes, and whether the button starts or stops."""
        match view_model.primary_action:
            case ConverterAction.CANCEL:
                callback: VoidCallback = self._on_cancel_clicked
                theme = self._theme_cancel
                self._status_message = self._msg_cancel
            case ConverterAction.CONVERT:
                callback = self._on_convert_clicked
                theme = self._theme_convert
                self._status_message = self._msg_convert

        dpg_configure_item(
            TAG_MAIN_CONVERTER_BUTTON_ACTION,
            label=view_model.action_label,
            enabled=view_model.primary_action_enabled,
        )
        dpg_set_item_callback(TAG_MAIN_CONVERTER_BUTTON_ACTION, callback)
        if self._button is not None and theme is not None:
            self._button.set_theme(theme)

        dpg_configure_item(
            TAG_MAIN_CONVERTER_TOOLTIP_CONVERT,
            show=view_model.other_operation_active and view_model.primary_action == ConverterAction.CONVERT,
        )

    def _explanation(self, *_args: Any, **_kwargs: Any) -> str:
        return self._status_message

    def _on_convert_clicked(self) -> None:
        self.call(self.on_convert_requested)

    def _on_cancel_clicked(self) -> None:
        self.call(self.on_cancel_requested)
