from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar

import dearpygui.dearpygui as dpg

from constants.browser import (
    CLR_PATH_TEXT,
    DIM_DIALOG_ERROR_HEIGHT,
    DIM_DIALOG_ERROR_WIDTH,
    LBL_BUTTON_OK,
    TAG_FILE_NOT_FOUND_DIALOG,
    TITLE_DIALOG_FILE_NOT_FOUND,
)
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
    width: int = DIM_DIALOG_ERROR_WIDTH,
    height: int = DIM_DIALOG_ERROR_HEIGHT,
) -> None:
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)

    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        width=width,
        height=height,
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


def show_file_not_found_dialog(filepath: Path, message: str) -> None:
    def content(parent: str) -> None:
        dpg.add_text(message, parent=parent)
        dpg.add_text(str(filepath), color=CLR_PATH_TEXT, wrap=DIM_DIALOG_ERROR_WIDTH - 10, parent=parent)

    show_modal_dialog(
        tag=TAG_FILE_NOT_FOUND_DIALOG,
        title=TITLE_DIALOG_FILE_NOT_FOUND,
        content=content,
    )
