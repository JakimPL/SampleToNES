import dearpygui.dearpygui as dpg

from sampletones_application.constants.main import (
    TAG_DIALOG_MAIN_CONVERTER_SUCCESS,
)
from sampletones_application.text.elements.main import ConverterElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.utils.dialogs import show_modal_dialog
from sampletones_application.utils.dpg import dpg_delete_item


class ConverterSuccessDialog:
    def __init__(self, *, language_manager: LanguageManager) -> None:
        self._msg_success = language_manager[
            TextKey(Page.MAIN, Panel.CONVERTER, TextType.MESSAGE, ConverterElements.STATUS_SUCCESS)
        ]
        self._ttl_progress = language_manager[
            TextKey(Page.MAIN, Panel.CONVERTER, TextType.TITLE, ConverterElements.PROGRESS_DIALOG)
        ]

    def show(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(self._msg_success, parent=parent)

        dpg_delete_item(TAG_DIALOG_MAIN_CONVERTER_SUCCESS)
        show_modal_dialog(
            tag=TAG_DIALOG_MAIN_CONVERTER_SUCCESS,
            title=self._ttl_progress,
            content=content,
        )
