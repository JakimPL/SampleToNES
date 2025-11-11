from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from application.config.manager import ConfigManager
from application.elements.path import GUIPathText
from application.utils.dialogs import show_error_dialog, show_modal_dialog
from constants.browser import (
    DIM_CONVERTER_BUTTON_WIDTH,
    DIM_DIALOG_CONVERTER_HEIGHT,
    DIM_DIALOG_CONVERTER_WIDTH,
    LBL_BUTTON_CANCEL,
    LBL_BUTTON_CLOSE,
    LBL_BUTTON_LOAD,
    MSG_CONVERTER_CANCELLED,
    MSG_CONVERTER_CANCELLING,
    MSG_CONVERTER_COMPLETED,
    MSG_CONVERTER_ERROR,
    MSG_CONVERTER_IDLE,
    MSG_CONVERTER_PROCESSING,
    MSG_CONVERTER_SUCCESS,
    MSG_INPUT_PATH_PREFIX,
    MSG_OUTPUT_PATH_PREFIX,
    TAG_CONVERTER_CANCEL_BUTTON,
    TAG_CONVERTER_INPUT_PATH_TEXT,
    TAG_CONVERTER_LOAD_BUTTON,
    TAG_CONVERTER_OUTPUT_PATH_TEXT,
    TAG_CONVERTER_PROGRESS,
    TAG_CONVERTER_STATUS,
    TAG_CONVERTER_SUCCESS_DIALOG,
    TAG_CONVERTER_WINDOW,
    TITLE_DIALOG_CONVERTER,
    TPL_CONVERTER_STATUS,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from reconstructor.converter.converter import ReconstructionConverter
from reconstructor.converter.paths import get_output_path
from utils.parallelization.task import TaskProgress, TaskStatus


class GUIConverterWindow:
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.converter: Optional[ReconstructionConverter] = None
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        self.is_file: bool = False
        self.output_path: Optional[Path] = None

        self._on_load_file: Optional[Callable[[Path], None]] = None
        self._on_load_directory: Optional[Callable[[], None]] = None

    def hide(self) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            dpg.delete_item(TAG_CONVERTER_WINDOW)

    def show(self, input_path: Path, is_file: bool = False) -> None:
        self.is_file = is_file

        config = self.config_manager.get_config()
        self.converter = ReconstructionConverter(config=config)
        self.converter.set_callbacks(
            on_complete=self._on_conversion_complete,
            on_error=self._on_conversion_error,
            on_cancelled=self._on_cancellation_complete,
            on_progress=self._update_status,
        )

        self.output_path = get_output_path(config, input_path)

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

            self.input_path_text = GUIPathText(
                path=input_path,
                prefix=MSG_INPUT_PATH_PREFIX,
                tag=TAG_CONVERTER_INPUT_PATH_TEXT,
                parent=TAG_CONVERTER_WINDOW,
            )

            self.output_path_text = GUIPathText(
                path=self.output_path,
                prefix=MSG_OUTPUT_PATH_PREFIX,
                tag=TAG_CONVERTER_OUTPUT_PATH_TEXT,
                parent=TAG_CONVERTER_WINDOW,
            )

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

        self.converter.start(input_path, is_file)

    def _set_status_completed(self):
        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_COMPLETED)

    def _set_status_cancelling(self):
        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_CANCELLING)

    def _set_status_cancelled(self):
        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_CANCELLED)

    def _set_status_failed(self):
        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_ERROR)

    def _set_status_running(self, task_progress: TaskProgress):
        assert self.converter is not None, "Converter is not initialized"
        progress = task_progress.get_progress()
        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            dpg.set_value(TAG_CONVERTER_PROGRESS, progress)

        current_file = task_progress.current_item
        if self.input_path_text and current_file is not None:
            current_file_path = Path(current_file)
            self.input_path_text.set_path(current_file_path)

        if dpg.does_item_exist(TAG_CONVERTER_STATUS):
            dpg.set_value(
                TAG_CONVERTER_STATUS,
                TPL_CONVERTER_STATUS.format(self.converter.completed_files, self.converter.total_files),
            )

    def _update_status(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        if not dpg.does_item_exist(TAG_CONVERTER_WINDOW):
            return

        match task_status:
            case TaskStatus.COMPLETED:
                self._set_status_completed()
            case TaskStatus.FAILED:
                self._set_status_failed()
            case TaskStatus.CANCELLED:
                self._set_status_cancelled()
            case TaskStatus.CANCELLING:
                self._set_status_cancelling()
            case TaskStatus.RUNNING:
                self._set_status_running(task_progress)

    def _on_load_clicked(self) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_LOAD_BUTTON):
            dpg.configure_item(TAG_CONVERTER_LOAD_BUTTON, enabled=False)

        if self.is_file:
            if self.output_path and self._on_load_file is not None:
                self._on_load_file(self.output_path)
        else:
            if self._on_load_directory is not None:
                self._on_load_directory()

        self._on_close()

    def _on_cancel_clicked(self) -> None:
        self._cancel()

    def _on_cancellation_complete(self) -> None:
        self._rename_cancel_to_close()
        dpg.set_frame_callback(dpg.get_frame_count() + 30, self._on_close)

    def _rename_cancel_to_close(self) -> None:
        if dpg.does_item_exist(TAG_CONVERTER_CANCEL_BUTTON):
            dpg.configure_item(TAG_CONVERTER_CANCEL_BUTTON, label=LBL_BUTTON_CLOSE, enabled=True)
            dpg.configure_item
            dpg.set_item_callback(TAG_CONVERTER_CANCEL_BUTTON, self._on_close)

    def _cancel(self) -> None:
        if self.converter and self.converter.is_running():
            self._set_status_cancelling()
            self.converter.cancel()

    def _on_close(self) -> None:
        try:
            if self.converter and self.converter.is_running():
                self.converter.cancel()

            if self.converter:
                self.converter.cleanup()
        finally:
            self.hide()

    def _on_conversion_complete(self, output_path: Path) -> None:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_complete(output_path))

    def _finalize_complete(self, output_path: Path) -> None:
        self.set_completed(output_path)
        self._rename_cancel_to_close()
        self._show_success_dialog()

    def _on_conversion_error(self, exception: Exception) -> None:
        self._set_status_failed()
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_error(exception))

    def _finalize_error(self, exception: Exception) -> None:
        self._rename_cancel_to_close()
        show_error_dialog(exception, MSG_CONVERTER_ERROR)

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
            dpg.set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_PROCESSING.format(current_file))

    def set_completed(self, output_path: Path) -> None:
        if output_path.exists():
            self.output_path = output_path

        self._set_status_completed()
        if dpg.does_item_exist(TAG_CONVERTER_PROGRESS):
            dpg.set_value(TAG_CONVERTER_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)

        if dpg.does_item_exist(TAG_CONVERTER_LOAD_BUTTON):
            dpg.configure_item(TAG_CONVERTER_LOAD_BUTTON, enabled=True)

    def set_callbacks(
        self,
        on_load_file: Optional[Callable[[Path], None]] = None,
        on_load_directory: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_load_file is not None:
            self._on_load_file = on_load_file
        if on_load_directory is not None:
            self._on_load_directory = on_load_directory
