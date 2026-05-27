import dearpygui.dearpygui as dpg

from sampletones_application.constants.main import (
    MSG_MAIN_CONVERTER_SUCCESS,
    TAG_DIALOG_MAIN_CONVERTER_SUCCESS,
    TTL_DIALOG_MAIN_CONVERTER_PROGRESS,
)
from sampletones_application.utils.dialogs import show_modal_dialog
from sampletones_application.utils.dpg import dpg_delete_item


class ConverterSuccessDialog:
    def show(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_MAIN_CONVERTER_SUCCESS, parent=parent)

        dpg_delete_item(TAG_DIALOG_MAIN_CONVERTER_SUCCESS)
        show_modal_dialog(
            tag=TAG_DIALOG_MAIN_CONVERTER_SUCCESS,
            title=TTL_DIALOG_MAIN_CONVERTER_PROGRESS,
            content=content,
        )
