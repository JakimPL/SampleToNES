import threading
from pathlib import Path
from typing import Callable, Optional

from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    TPL_GLOBAL_TIME_ESTIMATION,
    VAL_DELAY_CANCEL,
    VAL_DELAY_SCHEDULE,
    VAL_GLOBAL_PROGRESS_COMPLETE,
    VAL_GLOBAL_PROGRESS_START,
    VAL_PRIORITY_SCHEDULE,
)
from sampletones_application.constants.main import (
    MSG_MAIN_CONVERTER_CANCELLED,
    MSG_MAIN_CONVERTER_CANCELLING,
    MSG_MAIN_CONVERTER_ERROR,
    MSG_MAIN_CONVERTER_GENERATING_LIBRARY,
    MSG_MAIN_CONVERTER_IDLE,
    MSG_MAIN_CONVERTER_RECONSTRUCTION_COMPLETED,
    MSG_MAIN_CONVERTER_WAITING,
    TPL_MAIN_CONVERTER_PROGRESS,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.progress import SystemProgress
from sampletones_application.view_model.main.converter import ConversionPhase, ConverterViewModel
from sampletones_core.configs import Config
from sampletones_core.parallelization import ETAEstimator, TaskProgress, TaskStatus
from sampletones_core.reconstructions.converter import ReconstructionConverter, get_output_path
from sampletones_shared.exceptions import NoFilesToProcessError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import to_path


class ConverterLogic(CallbackMixin):
    def __init__(self, config_manager: ConfigManager) -> None:
        self._config_manager = config_manager
        self._converter: Optional[ReconstructionConverter] = None
        self._eta_estimator: Optional[ETAEstimator] = None
        self._config: Optional[Config] = None
        self._status_lock = threading.Lock()
        self._phase: ConversionPhase = ConversionPhase.IDLE
        self._input_path: Optional[Path] = None
        self._output_path: Optional[Path] = None
        self._is_file: bool = True
        self._system_progress = SystemProgress()

        self.on_view_changed: Optional[Callable[[ConverterViewModel], None]] = None
        self.on_success: Optional[VoidCallback] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_no_files_to_process: Optional[VoidCallback] = None
        self.on_load_file: Optional[PathCallback] = None
        self.on_load_directory: Optional[VoidCallback] = None
        self.on_cancelled: Optional[VoidCallback] = None
        self.generate_library: Optional[VoidCallback] = None
        self.is_library_loaded: Optional[Callable[[], bool]] = None

    def is_running(self) -> bool:
        return self._converter is not None and (
            self._converter.is_running() or self._converter.status == TaskStatus.PENDING
        )

    def emit_initial_view(self) -> None:
        self._emit_view_model(MSG_MAIN_CONVERTER_IDLE, VAL_GLOBAL_PROGRESS_START, "0%")

    def set_input_path(self, input_path: Path, convert: bool = False) -> None:
        config = self._config_manager.config.model_copy()
        if not self._assign_paths(input_path, config):
            return

        if not self.is_running():
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(MSG_MAIN_CONVERTER_IDLE, VAL_GLOBAL_PROGRESS_START, "0%")

        if convert:
            self.start_conversion()

    def start_conversion(self) -> None:
        if self.is_running():
            logger.warning("Conversion is already in progress")
            return

        self._config = self._config_manager.config.model_copy()
        self._phase = ConversionPhase.WAITING
        self._emit_view_model(MSG_MAIN_CONVERTER_WAITING, VAL_GLOBAL_PROGRESS_START, "0%")
        self.call(self.generate_library)
        self._wait_for_library_and_start()

    def cancel(self) -> None:
        if self._converter and self._converter.is_running():
            self._phase = ConversionPhase.CANCELLING
            self._emit_view_model(MSG_MAIN_CONVERTER_CANCELLING, VAL_GLOBAL_PROGRESS_START, "0%")
            self._system_progress.error()
            self._converter.cancel()

    def close(self) -> None:
        try:
            if self._converter and self._converter.is_running():
                self._converter.cancel()
            if self._converter:
                self._converter.cleanup()
        finally:
            self._system_progress.clear()
            self._converter = None
            self._eta_estimator = None
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(MSG_MAIN_CONVERTER_IDLE, VAL_GLOBAL_PROGRESS_START, "0%")

    def handle_load_request(self) -> None:
        if self._is_file:
            if self._output_path:
                self.call(self.on_load_file, self._output_path)
        else:
            self.call(self.on_load_directory)

        self.close()

    def cleanup(self) -> None:
        if self._converter is not None and self._converter.is_running():
            self._converter.cancel()

        if self._converter is not None:
            self._converter.cleanup()

        self._system_progress.clear()
        self._converter = None
        self._eta_estimator = None

    def _assign_paths(self, input_path: Path, config: Config) -> bool:
        try:
            self._output_path = get_output_path(config, input_path)
            self._input_path = input_path
            self._is_file = input_path.is_file()
        except FileNotFoundError as exception:
            logger.error("Input file does not exist")
            self.call(self.on_error, exception)
            return False
        except OSError as exception:
            logger.error("Invalid path")
            self.call(self.on_error, exception)
            return False
        except Exception as exception:  # TODO: narrow down exception types
            logger.error("Failed to determine output path")
            self.call(self.on_error, exception)
            return False
        return True

    def _wait_for_library_and_start(self) -> None:
        if not self.call(self.is_library_loaded):
            self._emit_view_model(MSG_MAIN_CONVERTER_GENERATING_LIBRARY, VAL_GLOBAL_PROGRESS_START, "0%")
            CallbackQueue.add(
                self._wait_for_library_and_start,
                priority=VAL_PRIORITY_SCHEDULE,
                delay=VAL_DELAY_SCHEDULE,
            )
        else:
            self._start_conversion()

    def _start_conversion(self) -> None:
        assert self._input_path is not None, "Input path is not set"
        assert self._config is not None, "Config is not set"
        self._converter = ReconstructionConverter(
            config=self._config,
            input_path=self._input_path,
            is_file=self._is_file,
        )
        self._converter.set_callbacks(
            on_start=self._on_start,
            on_completed=self._on_conversion_complete,
            on_error=self._on_conversion_error,
            on_cancelled=self._on_cancellation_complete,
            on_progress=self._update_status,
        )
        self._converter.start()
        self._system_progress.initialize()

    def _on_start(self) -> None:
        assert self._converter is not None, "Converter is not initialized"
        tasks = self._converter.total_tasks
        self._eta_estimator = ETAEstimator(total=tasks)
        self._system_progress.start(tasks)

    def _on_conversion_complete(self, output_path: Path) -> None:
        if output_path.exists():
            self._output_path = output_path

        self._phase = ConversionPhase.COMPLETED
        self._emit_view_model(MSG_MAIN_CONVERTER_RECONSTRUCTION_COMPLETED, VAL_GLOBAL_PROGRESS_COMPLETE, "100%")
        self.call(self.on_success)

    def _on_conversion_error(self, exception: Exception) -> None:
        self._system_progress.error()
        self._phase = ConversionPhase.FAILED
        self._emit_view_model(MSG_MAIN_CONVERTER_ERROR, VAL_GLOBAL_PROGRESS_START, "100%")
        if isinstance(exception, NoFilesToProcessError):
            self.call(self.on_no_files_to_process)
        else:
            self.call(self.on_error, exception)

    def _on_cancellation_complete(self) -> None:
        self._phase = ConversionPhase.CANCELLED
        self._emit_view_model(MSG_MAIN_CONVERTER_CANCELLED, VAL_GLOBAL_PROGRESS_START, "100%")
        CallbackQueue.add(
            self.close,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_CANCEL,
        )
        self.call(self.on_cancelled)

    def _update_status(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        with self._status_lock:
            match task_status:
                case TaskStatus.CANCELLING:
                    self._phase = ConversionPhase.CANCELLING
                    self._emit_view_model(MSG_MAIN_CONVERTER_CANCELLING, task_progress.get_progress(), "0%")
                case TaskStatus.RUNNING:
                    self._handle_running_update(task_progress)
                case _:
                    pass

    def _handle_running_update(self, task_progress: TaskProgress) -> None:
        assert self._converter is not None, "Converter is not initialized"
        assert self._eta_estimator is not None, "ETA Estimator is not initialized"
        self._phase = ConversionPhase.RUNNING
        self._system_progress.set(task_progress.completed, task_progress.total)
        eta_string = self._eta_estimator.update(task_progress.completed)
        percent_string = self._eta_estimator.get_percent_string()
        status_text = TPL_MAIN_CONVERTER_PROGRESS.format(self._converter.completed_files, self._converter.total_files)

        if eta_string:
            status_text += TPL_GLOBAL_TIME_ESTIMATION.format(eta_string=eta_string)

        current_item = task_progress.current_item
        display_input_path = to_path(current_item) if current_item is not None else self._input_path
        self._emit_view_model(status_text, task_progress.get_progress(), percent_string, input_path=display_input_path)

    def _emit_view_model(
        self,
        status_text: str,
        progress: float,
        progress_overlay: str,
        input_path: Optional[Path] = None,
    ) -> None:
        display_output = (
            self._output_path if self._output_path is not None else self._config_manager.get_output_directory()
        )
        viewmodel = ConverterViewModel(
            phase=self._phase,
            status_text=status_text,
            progress=progress,
            progress_overlay=progress_overlay,
            input_path=input_path if input_path is not None else self._input_path,
            output_path=display_output,
            is_file=self._is_file,
        )
        self.call(self.on_view_changed, viewmodel)
