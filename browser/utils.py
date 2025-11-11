from functools import wraps
from pathlib import Path
from typing import Callable, Optional, TypeVar

import dearpygui.dearpygui as dpg

from browser.elements.path import GUIPathText
from constants.browser import (
    CLR_ERROR_TEXT,
    CLR_PATH_TEXT,
    DIM_DIALOG_ERROR_WIDTH_WRAP,
    DIM_DIALOG_HEIGHT,
    DIM_DIALOG_WIDTH,
    LBL_BUTTON_OK,
    MSG_LIBRARY_NOT_LOADED,
    MSG_RECONSTRUCTION_NO_DATA,
    SUF_GROUP,
    SUF_PATH_TEXT,
    TAG_ERROR_DIALOG,
    TAG_FILE_NOT_FOUND_DIALOG,
    TAG_LIBRARY_NOT_LOADED_DIALOG,
    TAG_PATH_MESSAGE_DIALOG,
    TAG_RECONSTRUCTION_NOT_LOADED_DIALOG,
    TITLE_DIALOG_ERROR,
    TITLE_DIALOG_FILE_NOT_FOUND,
    TITLE_DIALOG_LIBRARY_NOT_LOADED,
    TITLE_DIALOG_RECONSTRUCTION_NOT_LOADED,
)
from library.key import LibraryKey
from utils.serialization import SerializedData

T = TypeVar("T")


def file_dialog_handler(func: Callable[[T, Path], None]) -> Callable[[T, int, SerializedData], None]:
    @wraps(func)
    def wrapper(self: T, sender: int, app_data: SerializedData) -> None:
        if not app_data or "file_path_name" not in app_data:
            return

        filepath = app_data["file_path_name"]
        if not filepath:
            return

        filepath = Path(filepath)
        func(self, filepath)

    return wrapper


def show_modal_dialog(
    tag: str,
    title: str,
    content: Callable[[str], None],
    width: int = DIM_DIALOG_WIDTH,
    height: int = DIM_DIALOG_HEIGHT,
) -> None:
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)

    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        min_size=(width, height),
        no_resize=True,
        on_close=lambda: dpg.delete_item(tag),
    ):
        content(tag)
        dpg.add_separator()
        dpg.add_button(
            label=LBL_BUTTON_OK,
            callback=lambda: dpg.delete_item(tag),
            width=-1,
        )


def show_error_dialog(exception: Exception, message: Optional[str] = None) -> None:
    def content(parent: str) -> None:
        if message is not None:
            dpg.add_text(
                message,
                parent=parent,
                wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
            )
        dpg.add_text(
            str(exception),
            parent=parent,
            wrap=DIM_DIALOG_ERROR_WIDTH_WRAP,
            color=CLR_ERROR_TEXT,
        )

    show_modal_dialog(
        tag=TAG_ERROR_DIALOG,
        title=TITLE_DIALOG_ERROR,
        content=content,
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
