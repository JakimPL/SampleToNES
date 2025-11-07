from pathlib import Path
from typing import Callable, Optional, Union

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.converter.converter import ReconstructionConverter
from browser.utils import show_modal_dialog
from constants.browser import (
    CLR_PATH_TEXT,
    DIM_CONVERTER_BUTTON_WIDTH,
    DIM_DIALOG_CONVERTER_HEIGHT,
    DIM_DIALOG_CONVERTER_WIDTH,
    LBL_BUTTON_CANCEL,
    LBL_BUTTON_CLOSE,
    LBL_BUTTON_LOAD,
    MSG_CONVERTER_CANCELLED,
    MSG_CONVERTER_CANCELLING,
    MSG_CONVERTER_COMPLETED,
    MSG_CONVERTER_CONFIG_NOT_AVAILABLE,
    MSG_CONVERTER_ERROR_PREFIX,
    MSG_CONVERTER_IDLE,
    MSG_CONVERTER_SUCCESS,
    SUF_CONVERTER_HANDLER,
    TAG_CONVERTER_CANCEL_BUTTON,
    TAG_CONVERTER_ERROR_DIALOG,
    TAG_CONVERTER_LOAD_BUTTON,
    TAG_CONVERTER_PATH_TEXT,
    TAG_CONVERTER_PROGRESS,
    TAG_CONVERTER_STATUS,
    TAG_CONVERTER_SUCCESS_DIALOG,
    TAG_CONVERTER_WINDOW,
    TITLE_DIALOG_CONVERTER,
    TITLE_DIALOG_ERROR,
    TPL_CONVERTER_STATUS,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from utils.common import shorten_path


class GUIConverterWindow:
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.converter: Optional[ReconstructionConverter] = None

        self.target_path: Optional[Path] = None
        self.shortened_path: str = ""

        self.is_file: bool = False
        self.output_file_path: Optional[Path] = None

        self._on_load_file_callback: Optional[Callable[[Path], None]] = None
        self._on_load_directory_callback: Optional[Callable[[], None]] = None

    def hide(self) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            dpg.delete_item(TAG_CONVERTER_WINDOW)

    def show(self, target_path: Union[str, Path], is_file: bool = False) -> None:
        self.target_path = Path(target_path)
        self.shortened_path = shorten_path(self.target_path) if self.target_path else ""

        self.is_file = is_file
        self.output_file_path = None

        config = self.config_manager.get_config()
        if config is None:
            self._show_error_dialog(MSG_CONVERTER_CONFIG_NOT_AVAILABLE)
            return

        self.converter = ReconstructionConverter(config=config)
        self.converter.set_callbacks(
            on_complete=self._on_conversion_complete,
            on_error=self._on_conversion_error,
            on_cancelled=self._on_cancellation_complete,
        )

        self.hide()
        with dpg.window(
            label=TITLE_DIALOG_CONVERTER,
            tag=TAG_CONVERTER_WINDOW,
            modal=True,
            width=DIM_DIALOG_CONVERTER_WIDTH,
            height=DIM_DIALOG_CONVERTER_HEIGHT,
            no_resize=True,
            on_close=self._on_close,
        ):
            dpg.add_text(MSG_CONVERTER_IDLE, tag=TAG_CONVERTER_STATUS)
            dpg.add_progress_bar(
                tag=TAG_CONVERTER_PROGRESS,
                default_value=VAL_GLOBAL_DEFAULT_FLOAT,
                width=-1,
            )
            dpg.add_text(
                self.shortened_path,
                tag=TAG_CONVERTER_PATH_TEXT,
                color=CLR_PATH_TEXT,
            )
            dpg.bind_item_handler_registry(TAG_CONVERTER_PATH_TEXT, self._create_path_handler())

            dpg.add_separator()

            with dpg.table(
                header_row=False,
                policy=dpg.mvTable_SizingStretchProp,
                resizable=False,
                width=-1,
            ):
                dpg.add_table_column()
                dpg.add_table_column()

                with dpg.table_row():
                    dpg.add_button(
                        label=LBL_BUTTON_LOAD,
                        tag=TAG_CONVERTER_LOAD_BUTTON,
                        width=DIM_CONVERTER_BUTTON_WIDTH,
                        callback=self._on_load_clicked,
                        enabled=False,
                    )
                    dpg.add_button(
                        label=LBL_BUTTON_CANCEL,
                        tag=TAG_CONVERTER_CANCEL_BUTTON,
                        width=DIM_CONVERTER_BUTTON_WIDTH,
                        callback=self._on_cancel_clicked,
                    )

        self.converter.start(self.target_path, self.is_file)
        dpg.set_frame_callback(dpg.get_frame_count() + 1, self._update_progress_callback)

    def _update_progress_callback(self) -> None:
        if not self.converter or not dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            return

        if self.converter.is_cancelling():
            if dpg.does_item_exist(TAG_CONVERTER_STATUS):
                dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_CANCELLING)
            if dpg.does_item_exist(TAG_CONVERTER_CANCEL_BUTTON):
                dpg.configure_item(TAG_CONVERTER_CANCEL_BUTTON, enabled=False)
            dpg.set_frame_callback(dpg.get_frame_count() + 10, self._update_progress_callback)
            return

        progress = self.converter.get_progress()
        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            dpg.set_value(TAG_CONVERTER_PROGRESS, progress)

        current_file = self.converter.get_current_file()
        if dpg.does_item_exist(TAG_CONVERTER_PATH_TEXT):
            if current_file is not None:
                dpg.set_value(TAG_CONVERTER_PATH_TEXT, shorten_path(Path(current_file)))
            elif self.target_path:
                dpg.set_value(TAG_CONVERTER_PATH_TEXT, self.shortened_path)

        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(
                TAG_CONVERTER_STATUS,
                TPL_CONVERTER_STATUS.format(self.converter.completed_files, self.converter.total_files),
            )

        if self.converter.is_running():
            dpg.set_frame_callback(dpg.get_frame_count() + 10, self._update_progress_callback)

    def _create_path_handler(self) -> str:
        handler_tag = f"{TAG_CONVERTER_PATH_TEXT}{SUF_CONVERTER_HANDLER}"
        if dpg.does_item_exist(handler_tag):
            dpg.delete_item(handler_tag)

        with dpg.item_handler_registry(tag=handler_tag):
            dpg.add_item_clicked_handler(callback=self._on_path_clicked)

        return handler_tag

    def _on_path_clicked(self) -> None:
        print(self.target_path)

    def _on_load_clicked(self) -> None:
        if self.is_file:
            if self.output_file_path and self._on_load_file_callback is not None:
                self._on_load_file_callback(self.output_file_path)
        else:
            if self._on_load_directory_callback is not None:
                self._on_load_directory_callback()

        self._on_close()

    def _on_cancel_clicked(self) -> None:
        if self.converter and self.converter.is_running():
            self.converter.cancel()

    def _on_cancellation_complete(self) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_CANCELLED)
        self._rename_cancel_to_close()
        dpg.set_frame_callback(dpg.get_frame_count() + 30, self._on_close)

    def _rename_cancel_to_close(self) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_CANCEL_BUTTON):
            dpg.configure_item(TAG_CONVERTER_CANCEL_BUTTON, label=LBL_BUTTON_CLOSE, enabled=True)
            dpg.set_item_callback(TAG_CONVERTER_CANCEL_BUTTON, self._on_close)

    def _on_close(self) -> None:
        if self.converter and self.converter.is_running():
            self.converter.cancel()

        self.hide()

    def _on_conversion_complete(self, output_path: Path) -> None:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_complete(output_path))

    def _finalize_complete(self, output_path: Path) -> None:
        self.set_completed(output_path)
        self._rename_cancel_to_close()
        self._show_success_dialog()

    def _on_conversion_error(self, error_message: str) -> None:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_error(error_message))

    def _finalize_error(self, error_message: str) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_ERROR_PREFIX)
        self._rename_cancel_to_close()
        self._show_error_dialog(error_message)

    def _show_error_dialog(self, error_message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_CONVERTER_ERROR_PREFIX, parent=parent)
            dpg.add_separator(parent=parent)
            dpg.add_text(error_message, wrap=DIM_DIALOG_CONVERTER_WIDTH - 20, parent=parent)

        show_modal_dialog(
            tag=TAG_CONVERTER_ERROR_DIALOG,
            title=TITLE_DIALOG_ERROR,
            content=content,
        )

    def _show_success_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_CONVERTER_SUCCESS, parent=parent)

        show_modal_dialog(
            tag=TAG_CONVERTER_SUCCESS_DIALOG,
            title=TITLE_DIALOG_CONVERTER,
            content=content,
        )

    def update_progress(self, progress: float, current_file: Optional[str] = None) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            dpg.set_value(TAG_CONVERTER_PROGRESS, progress)

        if current_file and dpg.does_item_exist(TAG_CONVERTER_STATUS):
            from constants.browser import MSG_CONVERTER_PROCESSING

            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_PROCESSING.format(current_file))

    def set_completed(self, output_path: Path) -> None:
        if output_path.exists():
            self.output_file_path = output_path

        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            dpg.set_value(TAG_CONVERTER_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)

        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_COMPLETED)

        if dpg.does_item_exist(TAG_CONVERTER_LOAD_BUTTON):
            dpg.configure_item(TAG_CONVERTER_LOAD_BUTTON, enabled=True)

    def set_callbacks(
        self,
        on_load_file_callback: Optional[Callable[[Path], None]] = None,
        on_load_directory_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_load_file_callback = on_load_file_callback
        self._on_load_directory_callback = on_load_directory_callback
