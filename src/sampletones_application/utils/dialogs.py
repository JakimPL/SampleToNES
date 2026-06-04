import uuid
from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
    TracebackElements,
)
from sampletones_application.categories.elements.reconstructions import (
    ReconstructionsDetailsElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TextKey
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_BUTTON_SAVE,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_GROUP,
    SUF_INFO_DIALOG,
    SUF_PATH_TEXT,
    TAG_GLOBAL_DIALOG_ERROR,
    TAG_GLOBAL_DIALOG_FILE_NOT_FOUND,
    TAG_GLOBAL_DIALOG_PATH_MESSAGE,
)
from sampletones_application.constants.reconstructions import (
    TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_NOT_LOADED,
)
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.trace import GUITraceback
from sampletones_application.utils.align import table_wrapper
from sampletones_application.utils.callbacks.frame import FrameCallbackManager
from sampletones_application.utils.dpg import (
    dpg_configure_item,
    dpg_delete_item,
)
from sampletones_shared.types.callback import Callback


def get_center(width: int, height: int) -> tuple[int, int]:
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


def _show_modal_dialog(
    tag: str,
    title: str,
    content: Callable[[str], None],
    *,
    ok_label: str,
    width: int,
    height: int,
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
            label=ok_label,
            callback=lambda: dpg_delete_item(tag),
            width=-1,
        )

        FrameCallbackManager.set_frame_callback(lambda: center_item(tag, width, height))


class DialogsRenderer:
    def __init__(self, *, layout: GeneralLayout, language_manager: LanguageManager) -> None:
        self._default_width = layout.dialogs.default.width
        self._default_height = layout.dialogs.default.height
        self._error_width = layout.dialogs.error.width
        self._error_height = layout.dialogs.error.height
        self._confirmation_height = layout.dialogs.confirmation.height
        self._default_wrap = layout.dialogs.default.width - 10
        self._error_wrap = layout.dialogs.error.width - 10
        self._col_text_error = layout.colors.text.error
        self._col_path = layout.colors.paths.default

        self._lbl_ok = language_manager[TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.OK)]
        self._lbl_cancel = language_manager[TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.CANCEL)]
        self._lbl_save = language_manager[TextKey(Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.SAVE)]
        self._lbl_traceback_show = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.TRACEBACK,
                TextType.LABEL,
                TracebackElements.SHOW,
            )
        ]
        self._lbl_traceback_hide = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.TRACEBACK,
                TextType.LABEL,
                TracebackElements.HIDE,
            )
        ]
        self._ttl_error = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.ERROR,
            )
        ]
        self._ttl_file_not_found = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.FILE_NOT_FOUND,
            )
        ]
        self._ttl_reconstruction_not_loaded = language_manager[
            TextKey(
                Page.RECONSTRUCTIONS,
                Panel.DETAILS,
                TextType.TITLE,
                ReconstructionsDetailsElements.NOT_LOADED_DIALOG,
            )
        ]
        self._msg_reconstruction_no_data = language_manager[
            TextKey(
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.MESSAGE,
                GlobalMessageElements.RECONSTRUCTION_NO_DATA,
            )
        ]

    def show_modal(
        self,
        tag: str,
        title: str,
        content: Callable[[str], None],
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        modal: bool = True,
    ) -> None:
        _show_modal_dialog(
            tag,
            title,
            content,
            ok_label=self._lbl_ok,
            width=width if width is not None else self._default_width,
            height=height if height is not None else self._default_height,
            modal=modal,
        )

    def show_info(self, tag: str, message: str, title: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._error_wrap)

        info_tag = f"{tag}{SUF_INFO_DIALOG}"
        dpg_delete_item(info_tag)
        _show_modal_dialog(
            tag=info_tag,
            title=title,
            content=content,
            ok_label=self._lbl_ok,
            width=self._default_width,
            height=self._default_height,
            modal=False,
        )

    def show_error(self, exception: Exception, message: Optional[str] = None) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_ERROR)

        with dpg.window(
            label=self._ttl_error,
            tag=tag,
            modal=True,
            min_size=(self._error_width, self._error_height),
            autosize=True,
            no_scrollbar=False,
            on_close=lambda: dpg_delete_item(tag),
        ):
            if message is not None:
                dpg.add_text(message, parent=tag, wrap=self._error_wrap)

            group_tag = f"{tag}{SUF_GROUP}"
            with dpg.group(tag=group_tag, parent=tag):
                dpg.add_text(
                    f"{str(type(exception).__name__)}: ",
                    parent=group_tag,
                    color=self._col_text_error,
                )
                dpg.add_text(
                    str(exception),
                    parent=group_tag,
                    wrap=self._error_wrap,
                    color=self._col_text_error,
                )

            traceback = GUITraceback(parent=tag, exception=exception)

            dpg.add_separator()

            @table_wrapper(columns=2)
            def content(_: None) -> None:
                show_button_tag = f"{tag}{SUF_BUTTON_SHOW_TRACEBACK}"

                def toggle_traceback() -> None:
                    traceback.toggle_visibility()
                    dpg_configure_item(
                        show_button_tag,
                        label=(self._lbl_traceback_show if not traceback.visible else self._lbl_traceback_hide),
                    )

                GUIButton(
                    tag=show_button_tag,
                    label=self._lbl_traceback_show,
                    width=-1,
                    callback=toggle_traceback,
                )
                GUIButton(
                    tag=f"{tag}{SUF_BUTTON_OK}",
                    label=self._lbl_ok,
                    callback=lambda: dpg_delete_item(tag),
                    width=-1,
                )

            content(None)

        FrameCallbackManager.set_frame_callback(lambda: center_item(tag, self._error_width, self._error_height))

    def show_file_not_found(self, filepath: Path, message: str) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._error_wrap)
            dpg.add_text(
                str(filepath),
                parent=parent,
                color=self._col_path,
                wrap=self._error_wrap,
            )

        _show_modal_dialog(
            tag=tag,
            title=self._ttl_file_not_found,
            content=content,
            ok_label=self._lbl_ok,
            width=self._error_width,
            height=self._default_height,
        )

    def show_confirmation(
        self,
        tag: str,
        message: str,
        title: str,
        on_confirm: Callback,
        *,
        ok_label: str,
    ) -> None:
        tag = get_dialog_tag(tag)

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._default_wrap)

            ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
            cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

            def disable() -> None:
                dpg_configure_item(ok_button_tag, enabled=False)
                dpg_configure_item(cancel_button_tag, enabled=False)

            def close() -> None:
                dpg_delete_item(tag)

            def _on_confirm() -> None:
                disable()
                on_confirm()
                close()

            def _on_cancel() -> None:
                disable()
                close()

            @table_wrapper(columns=2)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=ok_button_tag,
                    label=ok_label,
                    callback=_on_confirm,
                    width=-1,
                )
                GUIButton(
                    tag=cancel_button_tag,
                    label=self._lbl_cancel,
                    callback=_on_cancel,
                    width=-1,
                )

            buttons(None)

        with dpg.window(
            label=title,
            tag=tag,
            modal=True,
            min_size=(self._default_width, self._confirmation_height),
            no_resize=True,
            on_close=lambda: dpg_delete_item(tag),
        ):
            content(tag)

        FrameCallbackManager.set_frame_callback(
            lambda: center_item(tag, self._default_width, self._confirmation_height)
        )

    def show_save_confirmation(
        self,
        tag: str,
        message: str,
        title: str,
        on_save: Callback,
        on_confirm: Callback,
        *,
        ok_label: str,
    ) -> None:
        tag = get_dialog_tag(tag)

        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent, wrap=self._default_wrap)

            save_button_tag = f"{tag}{SUF_BUTTON_SAVE}"
            ok_button_tag = f"{tag}{SUF_BUTTON_OK}"
            cancel_button_tag = f"{tag}{SUF_BUTTON_CANCEL}"

            def disable() -> None:
                dpg_configure_item(save_button_tag, enabled=False)
                dpg_configure_item(ok_button_tag, enabled=False)
                dpg_configure_item(cancel_button_tag, enabled=False)

            def close() -> None:
                dpg_delete_item(tag)

            def _on_save() -> None:
                disable()
                on_save()
                on_confirm()
                close()

            def _on_confirm() -> None:
                disable()
                on_confirm()
                close()

            def _on_cancel() -> None:
                disable()
                close()

            @table_wrapper(columns=3)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=save_button_tag,
                    label=self._lbl_save,
                    callback=_on_save,
                    width=-1,
                )
                GUIButton(
                    tag=ok_button_tag,
                    label=ok_label,
                    callback=_on_confirm,
                    width=-1,
                )
                GUIButton(
                    tag=cancel_button_tag,
                    label=self._lbl_cancel,
                    callback=_on_cancel,
                    width=-1,
                )

            buttons(None)

        with dpg.window(
            label=title,
            tag=tag,
            modal=True,
            min_size=(self._default_width, self._confirmation_height),
            no_resize=True,
            on_close=lambda: dpg_delete_item(tag),
        ):
            content(tag)

        FrameCallbackManager.set_frame_callback(
            lambda: center_item(tag, self._default_width, self._confirmation_height)
        )

    def show_reconstruction_not_loaded(self) -> None:
        tag = get_dialog_tag(TAG_RECONSTRUCTIONS_RECONSTRUCTION_DIALOG_NOT_LOADED)

        def content(parent: str) -> None:
            dpg.add_text(
                self._msg_reconstruction_no_data,
                parent=parent,
                wrap=self._error_wrap,
            )

        _show_modal_dialog(
            tag=tag,
            title=self._ttl_reconstruction_not_loaded,
            content=content,
            ok_label=self._lbl_ok,
            width=self._error_width,
            height=self._default_height,
            modal=False,
        )

    def show_message_with_path(self, title: str, message: str, path: Path) -> None:
        tag = get_dialog_tag(TAG_GLOBAL_DIALOG_PATH_MESSAGE)

        def content(parent: str) -> None:
            group_tag = f"{parent}{SUF_GROUP}"
            with dpg.group(parent=parent):
                dpg.add_text(message, parent=group_tag, wrap=self._error_wrap)
                GUIPathText(
                    tag=f"{group_tag}{SUF_PATH_TEXT}",
                    path=path,
                    parent=group_tag,
                )

        _show_modal_dialog(
            tag=tag,
            title=title,
            content=content,
            ok_label=self._lbl_ok,
            width=self._error_width,
            height=self._default_height,
            modal=False,
        )
