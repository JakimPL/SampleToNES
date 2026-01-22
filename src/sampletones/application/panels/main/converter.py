import threading
from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.configs import Config
from sampletones.exceptions import NoFilesToProcessError
from sampletones.parallelization import ETAEstimator, TaskProgress, TaskStatus
from sampletones.reconstructions.converter import (
    ReconstructionConverter,
    get_output_path,
)
from sampletones.types import PathCallback, VoidCallback
from sampletones.utils import to_path
from sampletones.utils.logger import logger

from ...config.manager import ConfigManager
from ...constants.general import (
    TPL_GLOBAL_TIME_ESTIMATION,
    VAL_DELAY_CANCEL,
    VAL_DELAY_SCHEDULE,
    VAL_GLOBAL_PROGRESS_COMPLETE,
    VAL_GLOBAL_PROGRESS_START,
    VAL_PRIORITY_SCHEDULE,
)
from ...constants.main import (
    DIM_BUTTON_HEIGHT_MAIN_CONVERTER,
    DIM_BUTTON_WIDTH_MAIN_CONVERTER,
    DIM_PANEL_HEIGHT_MAIN_CONVERTER,
    LBL_BUTTON_MAIN_CONVERTER_CANCEL,
    LBL_BUTTON_MAIN_CONVERTER_CLOSE,
    LBL_BUTTON_MAIN_CONVERTER_CONVERT_DIRECTORY,
    LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE,
    LBL_BUTTON_MAIN_CONVERTER_LOAD,
    LBL_SECTION_MAIN_CONVERTER,
    MSG_MAIN_CONVERTER_CANCELLED,
    MSG_MAIN_CONVERTER_CANCELLING,
    MSG_MAIN_CONVERTER_ERROR,
    MSG_MAIN_CONVERTER_GENERATING_LIBRARY,
    MSG_MAIN_CONVERTER_IDLE,
    MSG_MAIN_CONVERTER_INPUT,
    MSG_MAIN_CONVERTER_NO_FILES_TO_PROCESS,
    MSG_MAIN_CONVERTER_OUTPUT,
    MSG_MAIN_CONVERTER_RECONSTRUCTION_COMPLETED,
    MSG_MAIN_CONVERTER_SUCCESS,
    MSG_MAIN_CONVERTER_WAITING,
    TAG_BUTTON_MAIN_CONVERTER_CANCEL,
    TAG_BUTTON_MAIN_CONVERTER_CONVERT,
    TAG_BUTTON_MAIN_CONVERTER_LOAD,
    TAG_DIALOG_MAIN_CONVERTER_SUCCESS,
    TAG_GROUP_MAIN_CONVERTER,
    TAG_PANEL_MAIN,
    TAG_PANEL_MAIN_CONVERTER,
    TAG_PATH_MAIN_CONVERTER_INPUT_PATH,
    TAG_PROGRESS_MAIN_CONVERTER,
    TAG_TEXT_MAIN_CONVERTER_OUTPUT_PATH,
    TAG_TEXT_MAIN_CONVERTER_STATUS,
    TPL_MAIN_CONVERTER_PROGRESS,
    TTL_DIALOG_MAIN_CONVERTER_PROGRESS,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.panel import GUIPanel
from ...elements.path import GUIPathText
from ...utils.align import table_wrapper
from ...utils.callbacks.queue import CallbackQueue
from ...utils.dialogs import show_error_dialog, show_info_dialog, show_modal_dialog
from ...utils.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_set_item_callback,
    dpg_set_value,
)
from ...utils.progress import SystemProgress


class GUIConverterPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        self.converter: Optional[ReconstructionConverter] = None
        self.system_progress = SystemProgress()

        self.eta_estimator: Optional[ETAEstimator] = None

        self._status_lock = threading.Lock()

        self.config: Optional[Config] = None
        self.is_file: bool = True
        self.input_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.input_path_text: Optional[GUIPathText] = None
        self.output_path_text: Optional[GUIPathText] = None

        self.on_load_file: Optional[PathCallback] = None
        self.on_load_directory: Optional[VoidCallback] = None
        self.on_cancelled: Optional[VoidCallback] = None
        self.generate_library: Optional[VoidCallback] = None
        self.is_library_loaded: Optional[Callable[[], bool]] = None

        super().__init__(
            tag=TAG_PANEL_MAIN_CONVERTER,
            parent=TAG_PANEL_MAIN,
            height=DIM_PANEL_HEIGHT_MAIN_CONVERTER,
        )

    def set_input_path(self, input_path: Path, convert: bool = False) -> None:
        config = self._get_config()

        if not self._assign_paths(input_path, config):
            return

        if not self.is_converter_running():
            self._set_conversion_subpanel_visible(False)
            dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_IDLE)

        if convert:
            self._prepare_conversion()

    def is_converter_running(self) -> bool:
        return self.converter is not None and (
            self.converter.is_running() or self.converter.status == TaskStatus.PENDING
        )

    def _prepare_conversion(self) -> None:
        if self.is_converter_running():
            logger.warning("Conversion is already in progress")
            return

        self.config = self._get_config()
        self._set_conversion_panel_enabled(False)
        self._set_conversion_subpanel_visible(True)
        self._reset_progress()
        self._update_paths()
        self.call(self.generate_library)
        self._wait_for_library_and_start()

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            parent=self.parent,
            width=self.width,
            height=self.height,
            border=False,
        ):
            self._create_section_text()
            self._create_export_button()
            self._create_paths()
            self._create_conversion_status()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_CONVERTER)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_export_button(self) -> None:
        dpg.add_separator()
        label = (
            LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE if self.is_file else LBL_BUTTON_MAIN_CONVERTER_CONVERT_DIRECTORY
        )
        enabled = self.input_path is not None and not self.is_converter_running()
        GUIButton(
            label=label,
            tag=TAG_BUTTON_MAIN_CONVERTER_CONVERT,
            width=DIM_BUTTON_WIDTH_MAIN_CONVERTER,
            height=DIM_BUTTON_HEIGHT_MAIN_CONVERTER,
            font=Font.BOLD_LARGE,
            enabled=enabled,
            callback=self._prepare_conversion,
        )

    def _create_paths(self) -> None:
        self.input_path_text = GUIPathText(
            path=self.input_path,
            prefix=MSG_MAIN_CONVERTER_INPUT,
            tag=TAG_PATH_MAIN_CONVERTER_INPUT_PATH,
            parent=TAG_GROUP_MAIN_CONVERTER,
            font=Font.REGULAR_SMALL,
        )

        self.output_path_text = GUIPathText(
            path=self.config_manager.get_output_directory(),
            prefix=MSG_MAIN_CONVERTER_OUTPUT,
            tag=TAG_TEXT_MAIN_CONVERTER_OUTPUT_PATH,
            parent=TAG_GROUP_MAIN_CONVERTER,
            font=Font.REGULAR_SMALL,
        )

    def _create_conversion_status(self) -> None:
        with dpg.group(
            tag=TAG_GROUP_MAIN_CONVERTER,
            parent=self.tag,
            show=False,
        ):
            dpg.add_separator()
            dpg.add_text(
                MSG_MAIN_CONVERTER_WAITING,
                tag=TAG_TEXT_MAIN_CONVERTER_STATUS,
                parent=TAG_GROUP_MAIN_CONVERTER,
            )
            dpg.add_progress_bar(
                tag=TAG_PROGRESS_MAIN_CONVERTER,
                parent=TAG_GROUP_MAIN_CONVERTER,
                default_value=VAL_GLOBAL_PROGRESS_START,
                width=-1,
                overlay="0%",
            )

            dpg.add_separator()
            self._add_buttons()

    def _update_paths(self) -> None:
        if self.is_converter_running():
            return

        if self.input_path is None or self.output_path is None:
            return

        label = (
            f"{LBL_BUTTON_MAIN_CONVERTER_CONVERT_SAMPLE}"
            if self.is_file
            else f"{LBL_BUTTON_MAIN_CONVERTER_CONVERT_DIRECTORY}"
        )
        label += f": {self.input_path.name}"
        dpg_configure_item(
            TAG_BUTTON_MAIN_CONVERTER_CONVERT,
            label=label,
            enabled=True,
        )

        if self.input_path_text is not None:
            self.input_path_text.set_path(self.input_path)

        if self.output_path_text is not None:
            self.output_path_text.set_path(self.output_path)

    def _wait_for_library_and_start(self) -> None:
        if not self.call(self.is_library_loaded):
            dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_GENERATING_LIBRARY)
            CallbackQueue.add(
                self._wait_for_library_and_start,
                priority=VAL_PRIORITY_SCHEDULE,
                delay=VAL_DELAY_SCHEDULE,
            )
        else:
            self._start_conversion()

    def _get_config(self) -> Config:
        return self.config_manager.config.model_copy()

    def _assign_paths(self, input_path: Path, config: Config) -> bool:
        try:
            self.output_path = get_output_path(config, input_path)
            self.input_path = input_path
            self.is_file = input_path.is_file()
        except FileNotFoundError as exception:
            logger.error("Input file does not exist")
            show_error_dialog(exception, MSG_MAIN_CONVERTER_ERROR)
            return False
        except OSError as exception:
            logger.error("Invalid path")
            show_error_dialog(exception, MSG_MAIN_CONVERTER_ERROR)
            return False
        except Exception as exception:
            logger.error("Failed to determine output path")
            show_error_dialog(exception, MSG_MAIN_CONVERTER_ERROR)
            return False

        self._update_paths()

        return True

    def _set_conversion_panel_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_CONVERT, enabled=enabled)

    def _set_conversion_subpanel_visible(self, visible: bool) -> None:
        dpg.configure_item(TAG_GROUP_MAIN_CONVERTER, show=visible)

    def _start_conversion(self) -> None:
        assert self.input_path is not None, "Input path is not set"
        assert self.config is not None, "Config is not set"

        self.converter = ReconstructionConverter(
            config=self.config,
            input_path=self.input_path,
            is_file=self.is_file,
        )
        self.converter.set_callbacks(
            on_start=self._on_start,
            on_completed=self._on_conversion_complete,
            on_error=self._on_conversion_error,
            on_cancelled=self._on_cancellation_complete,
            on_progress=self._update_status,
        )

        self.converter.start()
        self.system_progress.initialize()

    @table_wrapper(columns=2)
    def _add_buttons(self) -> None:
        GUIButton(
            label=LBL_BUTTON_MAIN_CONVERTER_LOAD,
            tag=TAG_BUTTON_MAIN_CONVERTER_LOAD,
            width=DIM_BUTTON_WIDTH_MAIN_CONVERTER,
            callback=self._on_load_clicked,
            enabled=False,
        )
        GUIButton(
            label=LBL_BUTTON_MAIN_CONVERTER_CANCEL,
            tag=TAG_BUTTON_MAIN_CONVERTER_CANCEL,
            width=DIM_BUTTON_WIDTH_MAIN_CONVERTER,
            callback=self._on_cancel_clicked,
        )

    def _set_status_completed(self) -> None:
        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_RECONSTRUCTION_COMPLETED)
        self._set_conversion_panel_enabled(True)

    def _set_status_cancelling(self) -> None:
        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_CANCELLING)

    def _set_status_cancelled(self) -> None:
        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_CANCELLED)
        self._set_conversion_panel_enabled(True)

    def _set_status_failed(self) -> None:
        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_ERROR)
        self._set_conversion_panel_enabled(True)

    def _set_status_running(self, task_progress: TaskProgress) -> None:
        assert self.converter is not None, "Converter is not initialized"
        self._update_progress(task_progress)

        current_file = task_progress.current_item
        if self.input_path_text and current_file is not None:
            current_file_path = to_path(current_file)
            self.input_path_text.set_path(current_file_path)

    def _update_status(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        if not dpg.does_item_exist(TAG_GROUP_MAIN_CONVERTER):
            return None

        with self._status_lock:
            match task_status:
                case TaskStatus.COMPLETED:
                    return self._set_status_completed()
                case TaskStatus.FAILED:
                    return self._set_status_failed()
                case TaskStatus.CANCELLED:
                    return self._set_status_cancelled()
                case TaskStatus.CANCELLING:
                    return self._set_status_cancelling()
                case TaskStatus.RUNNING:
                    return self._set_status_running(task_progress)

        return None

    def _on_load_clicked(self) -> None:
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_LOAD, enabled=False)

        if self.is_file:
            if self.output_path:
                self.call(self.on_load_file, self.output_path)
        else:
            self.call(self.on_load_directory)

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
        CallbackQueue.add(
            self._on_close,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_CANCEL,
        )
        self.call(self.on_cancelled)

    def _reset_progress(self) -> None:
        dpg_set_value(TAG_PROGRESS_MAIN_CONVERTER, VAL_GLOBAL_PROGRESS_START)
        dpg_configure_item(TAG_PROGRESS_MAIN_CONVERTER, overlay="0%")
        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, MSG_MAIN_CONVERTER_WAITING)

    def _rename_cancel_to_close(self) -> None:
        dpg_set_value(TAG_PROGRESS_MAIN_CONVERTER, VAL_GLOBAL_PROGRESS_START)
        dpg_configure_item(TAG_PROGRESS_MAIN_CONVERTER, overlay="100%")
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_CANCEL, label=LBL_BUTTON_MAIN_CONVERTER_CLOSE, enabled=True)
        dpg_set_item_callback(TAG_BUTTON_MAIN_CONVERTER_CANCEL, self._on_close)

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
            self.converter = None
            self.eta_estimator = None
            self._set_conversion_subpanel_visible(False)

    def _on_conversion_complete(self, output_path: Path) -> None:
        self._set_completed(output_path)
        self._rename_cancel_to_close()
        self._show_success_dialog()

    def _on_conversion_error(self, exception: Exception) -> None:
        self.system_progress.error()
        self._rename_cancel_to_close()
        if isinstance(exception, NoFilesToProcessError):
            show_info_dialog(
                self.tag,
                MSG_MAIN_CONVERTER_NO_FILES_TO_PROCESS,
                TTL_DIALOG_MAIN_CONVERTER_PROGRESS,
            )
            return

        self._set_status_failed()
        show_error_dialog(exception, MSG_MAIN_CONVERTER_ERROR)

    def _show_success_dialog(self) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_MAIN_CONVERTER_SUCCESS, parent=parent)

        dpg_delete_item(TAG_DIALOG_MAIN_CONVERTER_SUCCESS)
        show_modal_dialog(
            tag=TAG_DIALOG_MAIN_CONVERTER_SUCCESS,
            title=TTL_DIALOG_MAIN_CONVERTER_PROGRESS,
            content=content,
        )

    def _update_progress(self, task_progress: TaskProgress) -> None:
        assert self.converter is not None, "Converter is not initialized"
        assert self.eta_estimator is not None, "ETA Estimator is not initialized"

        dpg_set_value(TAG_PROGRESS_MAIN_CONVERTER, task_progress.get_progress())
        eta_string = self.eta_estimator.update(task_progress.completed)
        percent_string = self.eta_estimator.get_percent_string()
        dpg_configure_item(TAG_PROGRESS_MAIN_CONVERTER, overlay=percent_string)
        self.system_progress.set(task_progress.completed, task_progress.total)

        status_text = TPL_MAIN_CONVERTER_PROGRESS.format(self.converter.completed_files, self.converter.total_files)
        if eta_string:
            status_text += TPL_GLOBAL_TIME_ESTIMATION.format(eta_string=eta_string)

        dpg_set_value(TAG_TEXT_MAIN_CONVERTER_STATUS, status_text)

    def _set_completed(self, output_path: Path) -> None:
        if output_path.exists():
            self.output_path = output_path

        self._set_status_completed()
        dpg_set_value(TAG_PROGRESS_MAIN_CONVERTER, VAL_GLOBAL_PROGRESS_COMPLETE)
        dpg_configure_item(TAG_PROGRESS_MAIN_CONVERTER, overlay="100%")
        dpg_configure_item(TAG_BUTTON_MAIN_CONVERTER_LOAD, enabled=True)
