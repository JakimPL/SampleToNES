from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.exceptions import NoFilesToProcessError
from sampletones.parallelization import ETAEstimator, TaskProgress, TaskStatus
from sampletones.reconstruction.converter import (
    ReconstructionConverter,
    get_output_path,
)
from sampletones.utils.logger import logger

from ..config.manager import ConfigManager
from ..constants import (
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
    MSG_CONVERTER_NO_FILES_TO_PROCESS,
    MSG_CONVERTER_SUCCESS,
    MSG_INPUT_PATH_PREFIX,
    MSG_OUTPUT_PATH_PREFIX,
    TAG_BROWSER_CONTROLS_GROUP,
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
    TPL_TIME_ESTIMATION,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from ..elements.button import GUIButton
from ..elements.path import GUIPathText
from ..utils.dialogs import show_error_dialog, show_info_dialog, show_modal_dialog
from ..utils.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_item_callback,
    dpg_set_value,
)
from ..utils.status import SystemProgress


class GUIConverterWindow:
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.converter: Optional[ReconstructionConverter] = None
        self.system_progress = SystemProgress()

        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        self.eta_estimator: Optional[ETAEstimator] = None

        self.is_file: bool = False
        self.output_path: Optional[Path] = None

        self._on_load_file: Optional[Callable[[Path], None]] = None
        self._on_load_directory: Optional[Callable[[], None]] = None
        self._on_cancelled: Optional[Callable[[], None]] = None

    def hide(self) -> None:
        dpg_delete_item(TAG_CONVERTER_WINDOW)

    def show(self, input_path: Path, is_file: bool = False) -> None:
        self.hide()

        try:
            config = self.config_manager.get_config()
        except RuntimeError as exception:
            logger.error("Config not initialized")
            show_error_dialog(exception, MSG_CONVERTER_ERROR)
            return
        except Exception as exception:
            logger.error("Failed to get config")
            show_error_dialog(exception, MSG_CONVERTER_ERROR)
            return

        try:
            self.output_path = get_output_path(config, input_path)
        except FileNotFoundError as exception:
            logger.error("Input file does not exist")
            show_error_dialog(exception, MSG_CONVERTER_ERROR)
            return
        except OSError as exception:
            logger.error("Invalid path")
            show_error_dialog(exception, MSG_CONVERTER_ERROR)
            return
        except Exception as exception:
            logger.error("Failed to determine output path")
            show_error_dialog(exception, MSG_CONVERTER_ERROR)
            return

        self.is_file = is_file
        self.converter = ReconstructionConverter(
            config=config,
            input_path=input_path,
            is_file=is_file,
        )
        self.converter.set_callbacks(
            on_start=self._on_start,
            on_completed=self._on_conversion_complete,
            on_error=self._on_conversion_error,
            on_cancelled=self._on_cancellation_complete,
            on_progress=self._update_status,
        )

        dpg_configure_item(TAG_BROWSER_CONTROLS_GROUP, enabled=False)
        with dpg.window(
            label=TITLE_DIALOG_CONVERTER,
            tag=TAG_CONVERTER_WINDOW,
            modal=False,
            min_size=(DIM_DIALOG_CONVERTER_WIDTH, DIM_DIALOG_CONVERTER_HEIGHT),
            autosize=True,
            on_close=self._on_close,
        ):
            dpg.add_text(MSG_CONVERTER_IDLE, tag=TAG_CONVERTER_STATUS)
            dpg.add_progress_bar(
                tag=TAG_CONVERTER_PROGRESS,
                default_value=VAL_GLOBAL_DEFAULT_FLOAT,
                width=-1,
                overlay="0%",
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
                    GUIButton(
                        label=LBL_BUTTON_LOAD,
                        tag=TAG_CONVERTER_LOAD_BUTTON,
                        width=DIM_CONVERTER_BUTTON_WIDTH,
                        callback=self._on_load_clicked,
                        enabled=False,
                    )
                    GUIButton(
                        label=LBL_BUTTON_CANCEL,
                        tag=TAG_CONVERTER_CANCEL_BUTTON,
                        width=DIM_CONVERTER_BUTTON_WIDTH,
                        callback=self._on_cancel_clicked,
                    )

        self.converter.start()
        self.system_progress.initialize()

    def _set_status_completed(self):
        dpg_set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_COMPLETED)
        dpg_configure_item(TAG_BROWSER_CONTROLS_GROUP, enabled=True)

    def _set_status_cancelling(self):
        dpg_set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_CANCELLING)

    def _set_status_cancelled(self):
        dpg_set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_CANCELLED)
        dpg_configure_item(TAG_BROWSER_CONTROLS_GROUP, enabled=True)

    def _set_status_failed(self):
        dpg_set_value(TAG_CONVERTER_STATUS, MSG_CONVERTER_ERROR)
        dpg_configure_item(TAG_BROWSER_CONTROLS_GROUP, enabled=True)

    def _set_status_running(self, task_progress: TaskProgress):
        assert self.converter is not None, "Converter is not initialized"
        self._update_progress(task_progress)

        current_file = task_progress.current_item
        if self.input_path_text and current_file is not None:
            current_file_path = Path(current_file)
            self.input_path_text.set_path(current_file_path)

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
        dpg_configure_item(TAG_CONVERTER_LOAD_BUTTON, enabled=False)

        if self.is_file:
            if self.output_path and self._on_load_file is not None:
                self._on_load_file(self.output_path)
        else:
            if self._on_load_directory is not None:
                self._on_load_directory()

        self._on_close()

    def _on_start(self) -> None:
        assert self.converter is not None, "Converter is not initialized"
        tasks = self.converter.total_tasks
        self.eta_estimator = ETAEstimator(total=tasks)
        self.system_progress.start(tasks)

    def _on_cancel_clicked(self) -> None:
        self._cancel()

    def _on_cancellation_complete(self) -> None:
        self._rename_cancel_to_close()
        dpg.set_frame_callback(dpg.get_frame_count() + 30, self._on_close)
        if self._on_cancelled is not None:
            self._on_cancelled()

    def _rename_cancel_to_close(self) -> None:
        dpg_configure_item(TAG_CONVERTER_CANCEL_BUTTON, label=LBL_BUTTON_CLOSE, enabled=True)
        dpg_set_item_callback(TAG_CONVERTER_CANCEL_BUTTON, self._on_close)

    def _cancel(self) -> None:
        if self.converter and self.converter.is_running():
            self._set_status_cancelling()
            self.system_progress.error()
            self.converter.cancel()

    def _on_close(self) -> None:
        try:
            if self.converter and self.converter.is_running():
                self.converter.cancel()

            if self.converter:
                self.converter.cleanup()
        finally:
            self.system_progress.clear()
            self.hide()

    def _on_conversion_complete(self, output_path: Path) -> None:
        self.set_completed(output_path)
        self._rename_cancel_to_close()
        self._show_success_dialog()

    def _on_conversion_error(self, exception: Exception) -> None:
        self.system_progress.error()
        self._rename_cancel_to_close()
        if isinstance(exception, NoFilesToProcessError):
            dpg.set_frame_callback(
                dpg.get_frame_count() + 1,
                lambda: show_info_dialog(MSG_CONVERTER_NO_FILES_TO_PROCESS, TITLE_DIALOG_CONVERTER),
            )
            return

        self._set_status_failed()
        show_error_dialog(exception, MSG_CONVERTER_ERROR)

    def _show_success_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_CONVERTER_SUCCESS, parent=parent)

        show_modal_dialog(
            tag=TAG_CONVERTER_SUCCESS_DIALOG,
            title=TITLE_DIALOG_CONVERTER,
            content=content,
        )

    def _update_progress(self, task_progress: TaskProgress) -> None:
        assert self.converter is not None, "Converter is not initialized"
        assert self.eta_estimator is not None, "ETA Estimator is not initialized"

        dpg_set_value(TAG_CONVERTER_PROGRESS, task_progress.get_progress())
        eta_string = self.eta_estimator.update(task_progress.completed)
        percent_string = self.eta_estimator.get_percent_string()
        dpg_configure_item(TAG_CONVERTER_PROGRESS, overlay=percent_string)
        self.system_progress.set(task_progress.completed, task_progress.total)

        status_text = TPL_CONVERTER_STATUS.format(self.converter.completed_files, self.converter.total_files)
        if eta_string:
            status_text += TPL_TIME_ESTIMATION.format(eta_string=eta_string)

        dpg_set_value(TAG_CONVERTER_STATUS, status_text)

    def set_completed(self, output_path: Path) -> None:
        if output_path.exists():
            self.output_path = output_path

        self._set_status_completed()
        dpg_set_value(TAG_CONVERTER_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)
        dpg_configure_item(TAG_CONVERTER_PROGRESS, overlay="100%")
        dpg_configure_item(TAG_CONVERTER_LOAD_BUTTON, enabled=True)

    def set_callbacks(
        self,
        on_load_file: Optional[Callable[[Path], None]] = None,
        on_load_directory: Optional[Callable[[], None]] = None,
        on_cancelled: Optional[Callable[[], None]] = None,
    ) -> None:
        if on_load_file is not None:
            self._on_load_file = on_load_file
        if on_load_directory is not None:
            self._on_load_directory = on_load_directory
        if on_cancelled is not None:
            self._on_cancelled = on_cancelled
