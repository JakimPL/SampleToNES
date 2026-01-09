import uuid
from pathlib import Path
from typing import Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.typehints import Callback

from ..constants.general import (
    COL_PATH_TEXT,
    COL_TEXT_ERROR,
    DIM_DIALOG_HEIGHT,
    DIM_DIALOG_HEIGHT_CONFIRMATION,
    DIM_DIALOG_HEIGHT_ERROR,
    DIM_DIALOG_WIDTH,
    DIM_DIALOG_WIDTH_ERROR,
    DIM_DIALOG_WIDTH_ERROR_WRAP,
    DIM_DIALOG_WIDTH_WRAP,
    LBL_BUTTON_GLOBAL_CANCEL,
    LBL_BUTTON_GLOBAL_OK,
    LBL_BUTTON_GLOBAL_SAVE,
    LBL_BUTTON_TRACEBACK_HIDE,
    LBL_BUTTON_TRACEBACK_SHOW,
    MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_BUTTON_SAVE,
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
from ..constants.reconstructions import (
    TAG_RECONSTRUCTION_NOT_LOADED_DIALOG,
    TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_NOT_LOADED,
)
from ..elements.button import GUIButton
from ..elements.path import GUIPathText
from ..elements.trace import GUITraceback
from .align import table_wrapper
from .callbacks.frame import FrameCallbackManager
from .dpg import dpg_configure_item, dpg_delete_item


def get_center(width: int, height: int) -> Tuple[int, int]:
    x = (dpg.get_viewport_width() - width) / 2
    y = (dpg.get_viewport_height() - height) / 2
    return round(x), round(y)


def center_item(tag: str, width: int, height: int) -> None:
    if not dpg.does_item_exist(tag):
        return

    width, height = dpg.get_item_rect_size(tag)
    x, y = get_center(width, height)
    dpg.set_item_pos(tag, [x, y])


def get_dialog_tag(base_tag: str) -> str:
    dialog_hash = uuid.uuid4().hex
    return f"{base_tag}_{dialog_hash}"


def show_modal_dialog(
    tag: str,
    title: str,
    content: Callable[[str], None],
    width: int = DIM_DIALOG_WIDTH,
    height: int = DIM_DIALOG_HEIGHT,
    modal: bool = True,
) -> None:
    with dpg.window(
        label=title,
        tag=tag,
        modal=modal,
        width=width,
        min_size=(width, height),
        no_resize=True,
        autosize=True,
        on_close=lambda: dpg_delete_item(tag),
    ):
        content(tag)
        dpg.add_separator()
        ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
        GUIButton(
            tag=ok_button_tag,
            label=LBL_BUTTON_GLOBAL_OK,
            callback=lambda: dpg_delete_item(tag),
            width=-1,
        )

        FrameCallbackManager.set_frame_callback(lambda: center_item(tag, width, height))


def show_info_dialog(tag: str, message: str, title: str) -> None:
    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )

    info_tag = f"{tag}{SUF_INFO_DIALOG}"
    dpg_delete_item(info_tag)
    show_modal_dialog(
        tag=info_tag,
        title=title,
        content=content,
        modal=False,
    )


def show_confirmation_dialog(
    tag: str,
    message: str,
    title: str,
    on_confirm: Callback,
    width: int = DIM_DIALOG_WIDTH,
    height: int = DIM_DIALOG_HEIGHT_CONFIRMATION,
    ok_label: str = LBL_BUTTON_GLOBAL_OK,
) -> None:
    tag = get_dialog_tag(tag)

    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_WRAP,
        )

        ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
        cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

        def disable() -> None:
            dpg_configure_item(ok_button_tag, enabled=False)
            dpg_configure_item(cancel_button_tag, enabled=False)

        def close() -> None:
            dpg_delete_item(tag)

        @table_wrapper(columns=2)
        def buttons(_: None) -> None:
            GUIButton(
                tag=ok_button_tag,
                label=ok_label,
                callback=lambda: [disable(), on_confirm(), close()],
                width=-1,
            )
            GUIButton(
                tag=cancel_button_tag,
                label=LBL_BUTTON_GLOBAL_CANCEL,
                callback=lambda: [disable(), close()],
                width=-1,
            )

        buttons(None)

    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        min_size=(width, height),
        no_resize=True,
        on_close=lambda: dpg_delete_item(tag),
    ):
        content(tag)

    FrameCallbackManager.set_frame_callback(lambda: center_item(tag, width, height))


def show_save_confirmation_dialog(
    tag: str,
    message: str,
    title: str,
    on_save: Callback,
    on_confirm: Callback,
    width: int = DIM_DIALOG_WIDTH,
    height: int = DIM_DIALOG_HEIGHT_CONFIRMATION,
    ok_label=LBL_BUTTON_GLOBAL_OK,
) -> None:
    tag = get_dialog_tag(tag)

    def content(parent: str) -> None:
        dpg.add_text(
            message,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_WRAP,
        )

        save_button_tag = f"{tag}{SUF_BUTTON_SAVE}"
        ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
        cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

        def disable() -> None:
            dpg_configure_item(save_button_tag, enabled=False)
            dpg_configure_item(ok_button_tag, enabled=False)
            dpg_configure_item(cancel_button_tag, enabled=False)

        def close() -> None:
            dpg_delete_item(tag)

        @table_wrapper(columns=3)
        def buttons(_: None) -> None:
            GUIButton(
                tag=save_button_tag,
                label=LBL_BUTTON_GLOBAL_SAVE,
                callback=lambda: [disable(), on_save(), on_confirm(), close()],
                width=-1,
            )
            GUIButton(
                tag=ok_button_tag,
                label=ok_label,
                callback=lambda: [disable(), on_confirm(), close()],
                width=-1,
            )
            GUIButton(
                tag=cancel_button_tag,
                label=LBL_BUTTON_GLOBAL_CANCEL,
                callback=lambda: [disable(), close()],
                width=-1,
            )

        buttons(None)

    with dpg.window(
        label=title,
        tag=tag,
        modal=True,
        min_size=(width, height),
        no_resize=True,
        on_close=lambda: dpg_delete_item(tag),
    ):
        content(tag)

    FrameCallbackManager.set_frame_callback(lambda: center_item(tag, width, height))


def show_error_dialog(exception: Exception, message: Optional[str] = None) -> None:
    tag = get_dialog_tag(TAG_DIALOG_GLOBAL_ERROR)

    with dpg.window(
        label=TTL_DIALOG_ERROR,
        tag=tag,
        modal=True,
        min_size=(DIM_DIALOG_WIDTH_ERROR, DIM_DIALOG_HEIGHT_ERROR),
        autosize=True,
        no_scrollbar=False,
        on_close=lambda: dpg_delete_item(tag),
    ):
        if message is not None:
            dpg.add_text(
                message,
                parent=tag,
                wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
            )

        group_tag = f"{tag}{SUF_GROUP}"
        with dpg.group(tag=group_tag, parent=tag):
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
            parent=tag,
            exception=exception,
        )

        dpg.add_separator()

        @table_wrapper(columns=2)
        def content(_: None) -> None:
            show_button_tag = f"{tag}{SUF_BUTTON_SHOW_TRACEBACK}"

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
                tag=f"{tag}{SUF_BUTTON_OK}",
                label=LBL_BUTTON_GLOBAL_OK,
                callback=lambda: dpg_delete_item(tag),
                width=-1,
            )

        content(None)

    FrameCallbackManager.set_frame_callback(lambda: center_item(tag, DIM_DIALOG_WIDTH_ERROR, DIM_DIALOG_HEIGHT_ERROR))


def show_file_not_found_dialog(filepath: Path, message: str) -> None:
    tag = get_dialog_tag(TAG_DIALOG_GLOBAL_FILE_NOT_FOUND)

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
        tag=tag,
        title=TTL_DIALOG_FILE_NOT_FOUND,
        content=content,
        width=DIM_DIALOG_WIDTH_ERROR,
    )


def show_reconstruction_not_loaded_dialog() -> None:
    tag = get_dialog_tag(TAG_RECONSTRUCTION_NOT_LOADED_DIALOG)

    def content(parent: str) -> None:
        dpg.add_text(
            MSG_GLOBAL_RECONSTRUCTION_NO_DATA,
            parent=parent,
            wrap=DIM_DIALOG_WIDTH_ERROR_WRAP,
        )

    show_modal_dialog(
        tag=tag,
        title=TTL_DIALOG_RECONSTRUCTIONS_RECONSTRUCTION_NOT_LOADED,
        content=content,
        modal=False,
        width=DIM_DIALOG_WIDTH_ERROR,
    )


def show_message_with_path_dialog(title: str, message: str, path: Path) -> None:
    tag = get_dialog_tag(TAG_DIALOG_GLOBAL_PATH_MESSAGE)

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
        tag=tag,
        title=title,
        content=content,
        modal=False,
        width=DIM_DIALOG_WIDTH_ERROR,
    )
