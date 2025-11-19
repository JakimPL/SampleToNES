from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.library import LibraryKey

from ..constants import (
    CLR_ERROR_TEXT,
    CLR_PATH_TEXT,
    DIM_DIALOG_ERROR_HEIGHT,
    DIM_DIALOG_ERROR_WIDTH,
    DIM_DIALOG_ERROR_WIDTH_WRAP,
    DIM_DIALOG_HEIGHT,
    DIM_DIALOG_WIDTH,
    LBL_BUTTON_OK,
    LBL_BUTTON_SHOW_TRACEBACK,
    MSG_LIBRARY_NOT_LOADED,
    MSG_RECONSTRUCTION_NO_DATA,
    SUF_BUTTON_OK,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_GROUP,
    SUF_PATH_TEXT,
    TAG_BUTTON_OK,
    TAG_ERROR_DIALOG,
    TAG_FILE_NOT_FOUND_DIALOG,
    TAG_INFO_DIALOG,
    TAG_LIBRARY_NOT_LOADED_DIALOG,
    TAG_PATH_MESSAGE_DIALOG,
    TAG_RECONSTRUCTION_NOT_LOADED_DIALOG,
    TITLE_DIALOG_ERROR,
    TITLE_DIALOG_FILE_NOT_FOUND,
    TITLE_DIALOG_LIBRARY_NOT_LOADED,
    TITLE_DIALOG_RECONSTRUCTION_NOT_LOADED,
)
from ..elements.button import GUIButton
from ..elements.path import GUIPathText
from ..elements.trace import GUITraceback
from .dpg import dpg_delete_item


def show_modal_dialog(
    tag: str,
    title: str,
    content: Callable[[str], None],
    width: int = DIM_DIALOG_WIDTH,
    height: int = DIM_DIALOG_HEIGHT,
) -> None:
    dpg_delete_item(tag)

    with dpg.window(
        label=title,
        tag=tag,
        modal=False,  # changed to False to allow interaction with other windows
        min_size=(width, height),
        no_resize=True,
        on_close=lambda: dpg_delete_item(tag),
    ):
        content(tag)
        dpg.add_separator()
        GUIButton(
            tag=TAG_BUTTON_OK,
            label=LBL_BUTTON_OK,
            callback=lambda: dpg_delete_item(tag),
            width=-1,
        )


def show_info_dialog(message: str, title: str) -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
        )

    show_modal_dialog(
        tag=TAG_INFO_DIALOG,
        title=title,
        content=content,
    )


def show_error_dialog(exception: Exception, message: Optional[str] = None) -> None:
    dpg_delete_item(TAG_ERROR_DIALOG)

    with dpg.window(
        label=TITLE_DIALOG_ERROR,
        tag=TAG_ERROR_DIALOG,
        modal=False,
        min_size=(DIM_DIALOG_ERROR_WIDTH, DIM_DIALOG_ERROR_HEIGHT),
        autosize=True,
        on_close=lambda: dpg_delete_item(TAG_ERROR_DIALOG),
    ):
        if message is not None:
            dpg.add_text(
                message,
                parent=TAG_ERROR_DIALOG,
                wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
            )

        group_tag = f"{TAG_ERROR_DIALOG}{SUF_GROUP}"
        with dpg.group(tag=group_tag, parent=TAG_ERROR_DIALOG):
            dpg.add_text(
                f"{str(type(exception).__name__)}: ",
                parent=group_tag,
                color=CLR_ERROR_TEXT,
            )
            dpg.add_text(
                str(exception),
                parent=group_tag,
                wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
                color=CLR_ERROR_TEXT,
            )

        traceback = GUITraceback(
            parent=TAG_ERROR_DIALOG,
            exception=exception,
        )

        dpg.add_separator()

        with dpg.table(
            header_row=False,
            policy=dpg.mvTable_SizingStretchProp,
            resizable=False,
            width=-1,
            height=-1,
        ):
            dpg.add_table_column()
            dpg.add_table_column()

            with dpg.table_row():
                show_button_tag = f"{TAG_ERROR_DIALOG}{SUF_BUTTON_SHOW_TRACEBACK}"

                def toggle_traceback() -> None:
                    traceback.toggle_visibility()

                GUIButton(
                    tag=show_button_tag,
                    label=LBL_BUTTON_SHOW_TRACEBACK,
                    width=-1,
                    callback=toggle_traceback,
                )

                GUIButton(
                    tag=f"{TAG_ERROR_DIALOG}{SUF_BUTTON_OK}",
                    label=LBL_BUTTON_OK,
                    callback=lambda: dpg_delete_item(TAG_ERROR_DIALOG),
                    width=-1,
                )


def show_file_not_found_dialog(filepath: Path, message: str) -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
        )
        dpg.add_text(
            str(filepath),
            parent=parent,
            color=CLR_PATH_TEXT,
            wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
        )

    show_modal_dialog(
        tag=TAG_FILE_NOT_FOUND_DIALOG,
        title=TITLE_DIALOG_FILE_NOT_FOUND,
        content=content,
    )


def show_library_not_loaded_dialog(key: LibraryKey) -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            MSG_LIBRARY_NOT_LOADED.format(library_key=key),
            parent=parent,
            wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
        )

    show_modal_dialog(
        tag=TAG_LIBRARY_NOT_LOADED_DIALOG,
        title=TITLE_DIALOG_LIBRARY_NOT_LOADED,
        content=content,
    )


def show_reconstruction_not_loaded_dialog() -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            MSG_RECONSTRUCTION_NO_DATA,
            parent=parent,
            wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
        )

    show_modal_dialog(
        tag=TAG_RECONSTRUCTION_NOT_LOADED_DIALOG,
        title=TITLE_DIALOG_RECONSTRUCTION_NOT_LOADED,
        content=content,
    )


def show_message_with_path_dialog(title: str, message: str, path: Path) -> None:
    def content(parent: str) -> None:
        group_tag = f"{parent}{SUF_GROUP}"
        with dpg.group(parent=parent):
            dpg.add_text(
                message,
                parent=group_tag,
                wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
            )
            GUIPathText(
                tag=f"{group_tag}{SUF_PATH_TEXT}",
                path=path,
                parent=group_tag,
            )

    show_modal_dialog(
        tag=TAG_PATH_MESSAGE_DIALOG,
        title=title,
        content=content,
    )
