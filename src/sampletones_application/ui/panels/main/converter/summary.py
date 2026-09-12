from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.colors.path import PathColors
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_GROUP,
    TAG_MAIN_CONVERTER_GROUP_INPUT,
    TAG_MAIN_CONVERTER_GROUP_SUMMARY,
    TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
    TAG_MAIN_CONVERTER_PROGRESS,
    TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
    TAG_MAIN_CONVERTER_TEXT_STATUS,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.path import GUIDestinationPathText, GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.view_model.main.converter import ConverterViewModel


class ConverterSummary:
    """Where a run writes, and how far it has come.

    The destination stands whatever the list holds, so a reader always knows where a run would
    land. The input line names the recording a running conversion is on, and stands while it is
    reporting one.
    """

    def __init__(
        self,
        *,
        path_colors: PathColors,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._path_colors = path_colors
        self._status_bar = status_bar
        self._msg_path = language_manager["global.status.message.path"]
        self._msg_destination = language_manager["global.status.message.destination"]
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIDestinationPathText] = None

    def create_paths(self) -> None:
        """The recording a run is on, and the place its result lands."""
        dpg.add_separator()
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_SUMMARY):
            with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP_INPUT, show=False):
                self.input_path_text = GUIPathText(
                    path=None,
                    prefix=self._language_manager["main.converter.message.status_input_label"],
                    tag=TAG_MAIN_CONVERTER_PATH_INPUT_PATH,
                    parent=TAG_MAIN_CONVERTER_GROUP_INPUT,
                    color=self._path_colors.default,
                    hover_color=self._path_colors.hover,
                    status_message=self._msg_path,
                    font=Font.REGULAR_SMALL,
                    status_bar=self._status_bar,
                )

            self.output_path_text = GUIDestinationPathText(
                path=None,
                prefix=self._language_manager["main.converter.message.status_output_label"],
                tag=TAG_MAIN_CONVERTER_TEXT_OUTPUT_PATH,
                parent=TAG_MAIN_CONVERTER_GROUP_SUMMARY,
                color=self._path_colors.default,
                hover_color=self._path_colors.hover,
                status_message=self._msg_destination,
                font=Font.REGULAR_SMALL,
                status_bar=self._status_bar,
            )

    def create_status(self) -> None:
        """What the running conversion says it is doing, and how far along it is."""
        with dpg.group(tag=TAG_MAIN_CONVERTER_GROUP, show=False):
            status = dpg.add_text(
                self._language_manager["main.converter.message.status_waiting"],
                tag=TAG_MAIN_CONVERTER_TEXT_STATUS,
                parent=TAG_MAIN_CONVERTER_GROUP,
            )
            FontRegistry.bind_to_item(status, Font.MONO_SMALL)
            dpg.add_progress_bar(
                tag=TAG_MAIN_CONVERTER_PROGRESS,
                parent=TAG_MAIN_CONVERTER_GROUP,
                default_value=0.0,
                width=-1,
                overlay="0%",
            )
            FontRegistry.bind_to_item(TAG_MAIN_CONVERTER_PROGRESS, Font.MONO)

    def update_view(self, view_model: ConverterViewModel) -> None:
        """Name where the run writes, and say where it has got to."""
        if self.input_path_text is not None and view_model.input_path is not None:
            self.input_path_text.set_path(view_model.input_path)
        if self.output_path_text is not None and view_model.output_path is not None:
            self.output_path_text.set_path(view_model.output_path)

        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP_INPUT, show=view_model.shows_input)
        dpg_configure_item(TAG_MAIN_CONVERTER_GROUP, show=view_model.subpanel_visible)
        dpg_set_value(TAG_MAIN_CONVERTER_TEXT_STATUS, view_model.status_text)
        dpg_set_value(TAG_MAIN_CONVERTER_PROGRESS, view_model.progress)
        dpg_configure_item(TAG_MAIN_CONVERTER_PROGRESS, overlay=view_model.progress_overlay)
