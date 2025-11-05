from typing import Callable

import dearpygui.dearpygui as dpg

from constants.browser import (
    DIM_DIALOG_ERROR_HEIGHT,
    DIM_DIALOG_ERROR_WIDTH,
    LBL_BUTTON_OK,
)


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
