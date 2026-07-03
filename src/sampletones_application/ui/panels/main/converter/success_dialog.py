import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.main import ConverterElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.main import (
    TAG_MAIN_CONVERTER_DIALOG_SUCCESS,
)
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import dpg_delete_item


class ConverterSuccessDialog:
    def __init__(
        self,
        *,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
    ) -> None:
        self._dialogs = dialogs
        self._msg_success = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_SUCCESS,
        ]
        self._ttl_progress = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.TITLE,
            ConverterElements.PROGRESS_DIALOG,
        ]

    def show(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(self._msg_success, parent=parent)

        dpg_delete_item(TAG_MAIN_CONVERTER_DIALOG_SUCCESS)
        self._dialogs.show_modal(
            tag=TAG_MAIN_CONVERTER_DIALOG_SUCCESS,
            title=self._ttl_progress,
            content=content,
        )
