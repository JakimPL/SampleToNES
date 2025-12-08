from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.library import InstructionLibraryKey

from ..constants.general import (
    COL_PATH_TEXT,
    COL_TEXT_ERROR,
    DIM_DIALOG_HEIGHT,
    DIM_DIALOG_HEIGHT_ERROR,
    DIM_DIALOG_WIDTH,
    DIM_DIALOG_WIDTH_ERROR,
    DIM_DIALOG_WIDTH_ERROR_WRAP,
    LBL_BUTTON_GLOBAL_OK,
    LBL_BUTTON_TRACEBACK_HIDE,
    LBL_BUTTON_TRACEBACK_SHOW,
    MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
    SUF_BUTTON_OK,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_GROUP,
    SUF_INFO_DIALOG,
    SUF_PATH_TEXT,
    TAG_DIALOG_GLOBAL_ERROR,
    TAG_DIALOG_GLOBAL_FILE_NOT_FOUND,
    TAG_DIALOG_GLOBAL_PATH_MESSAGE,
    TTL_DIALOG_ERROR,
    TTL_DIALOG_FILE_NOT_FOUND,
)
from ..constants.instructions import (
    TAG_DIALOG_INSTRUCTIONS_LIBRARY_LIBRARY_NOT_LOADED,
    TPL_INSTRUCTIONS_LIBRARY_NOT_LOADED,
    TTL_DIALOG_LIBRARY_NOT_LOADED,
)
from ..constants.reconstructions import (
    TAG_RECONSTRUCTION_NOT_LOADED_DIALOG,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_NOT_LOADED,
)
from ..elements.button import GUIButton
from ..elements.path import GUIPathText
from ..elements.trace import GUITraceback
from .align import table_wrapper
from .dpg import dpg_configure_item, dpg_delete_item


def show_modal_dialog(
    tag: str,
    title: str,
    content: Callable[[str], None],
    width: int = DIM_DIALOG_WIDTH,
    height: int = DIM_DIALOG_HEIGHT,
    modal: bool = True,
) -> None:
    dpg_delete_item(tag)

    with dpg.window(
        label=title,
        tag=tag,
        modal=modal,
        min_size=(width, height),
        no_resize=True,
        on_close=lambda: dpg_delete_item(tag),
    ):
        content(tag)
        dpg.add_separator()
        button_ok_tag = f"{tag}{SUF_BUTTON_OK}"
        GUIButton(
            tag=button_ok_tag,
            label=LBL_BUTTON_GLOBAL_OK,
            callback=lambda: dpg_delete_item(tag),
            width=-1,
        )


def show_info_dialog(tag: str, message: str, title: str) -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )

    info_tag = f"{tag}{SUF_INFO_DIALOG}"
    show_modal_dialog(
        tag=info_tag,
        title=title,
        content=content,
        modal=False,
    )


def show_error_dialog(exception: Exception, message: Optional[str] = None) -> None:
    dpg_delete_item(TAG_DIALOG_GLOBAL_ERROR)

    with dpg.window(
        label=TTL_DIALOG_ERROR,
        tag=TAG_DIALOG_GLOBAL_ERROR,
        modal=True,
        min_size=(DIM_DIALOG_WIDTH_ERROR, DIM_DIALOG_HEIGHT_ERROR),
        autosize=True,
        on_close=lambda: dpg_delete_item(TAG_DIALOG_GLOBAL_ERROR),
    ):
        if message is not None:
            dpg.add_text(
                message,
                parent=TAG_DIALOG_GLOBAL_ERROR,
                wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
            )

        group_tag = f"{TAG_DIALOG_GLOBAL_ERROR}{SUF_GROUP}"
        with dpg.group(tag=group_tag, parent=TAG_DIALOG_GLOBAL_ERROR):
            dpg.add_text(
                f"{str(type(exception).__name__)}: ",
                parent=group_tag,
                color=COL_TEXT_ERROR,
            )
            dpg.add_text(
                str(exception),
                parent=group_tag,
                wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
                color=COL_TEXT_ERROR,
            )

        traceback = GUITraceback(
            parent=TAG_DIALOG_GLOBAL_ERROR,
            exception=exception,
        )

        dpg.add_separator()

        @table_wrapper(columns=2)
        def content(_: None) -> None:
            show_button_tag = f"{TAG_DIALOG_GLOBAL_ERROR}{SUF_BUTTON_SHOW_TRACEBACK}"

            def toggle_traceback() -> None:
                traceback.toggle_visibility()
                dpg_configure_item(
                    show_button_tag,
                    label=LBL_BUTTON_TRACEBACK_SHOW if not traceback.visible else LBL_BUTTON_TRACEBACK_HIDE,
                )

            GUIButton(
                tag=show_button_tag,
                label=LBL_BUTTON_TRACEBACK_SHOW,
                width=-1,
                callback=toggle_traceback,
            )

            GUIButton(
                tag=f"{TAG_DIALOG_GLOBAL_ERROR}{SUF_BUTTON_OK}",
                label=LBL_BUTTON_GLOBAL_OK,
                callback=lambda: dpg_delete_item(TAG_DIALOG_GLOBAL_ERROR),
                width=-1,
            )

        content(None)


def show_file_not_found_dialog(filepath: Path, message: str) -> None:
    dpg_delete_item(TAG_DIALOG_GLOBAL_FILE_NOT_FOUND)

    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )
        dpg.add_text(
            str(filepath),
            parent=parent,
            color=COL_PATH_TEXT,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )

    show_modal_dialog(
        tag=TAG_DIALOG_GLOBAL_FILE_NOT_FOUND,
        title=TTL_DIALOG_FILE_NOT_FOUND,
        content=content,
    )


def show_library_not_loaded_dialog(key: InstructionLibraryKey) -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            TPL_INSTRUCTIONS_LIBRARY_NOT_LOADED.format(library_key=key),
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )

    show_modal_dialog(
        tag=TAG_DIALOG_INSTRUCTIONS_LIBRARY_LIBRARY_NOT_LOADED,
        title=TTL_DIALOG_LIBRARY_NOT_LOADED,
        content=content,
        modal=False,
    )


def show_reconstruction_not_loaded_dialog() -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )

    show_modal_dialog(
        tag=TAG_RECONSTRUCTION_NOT_LOADED_DIALOG,
        title=TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_NOT_LOADED,
        content=content,
        modal=False,
    )


def show_message_with_path_dialog(title: str, message: str, path: Path) -> None:
    dpg_delete_item(TAG_DIALOG_GLOBAL_PATH_MESSAGE)

    def content(parent: str) -> None:
        group_tag = f"{parent}{SUF_GROUP}"
        with dpg.group(parent=parent):
            dpg.add_text(
                message,
                parent=group_tag,
                wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
            )
            GUIPathText(
                tag=f"{group_tag}{SUF_PATH_TEXT}",
                path=path,
                parent=group_tag,
            )

    show_modal_dialog(
        tag=TAG_DIALOG_GLOBAL_PATH_MESSAGE,
        title=title,
        content=content,
        modal=False,
    )
