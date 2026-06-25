from pathlib import Path
from typing import Callable, Optional

from sampletones_application.categories.elements.global_ import GlobalTemplateElements
from sampletones_application.categories.elements.main import ConverterElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.services.conversion import (
    ConversionResult,
    ConversionService,
)
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.progress import SystemProgress
from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)
from sampletones_core.configs import Config
from sampletones_core.parallelization import ETAEstimator, TaskProgress
from sampletones_core.reconstructions.converter import get_output_path
from sampletones_shared.exceptions import NoFilesToProcessError
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import to_path


class ConverterLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        conversion_service: ConversionService,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
    ) -> None:
        self._config_manager = config_manager
        self._service = conversion_service
        self._scheduling = scheduling
        self._msg_idle = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_IDLE,
        ]
        self._msg_waiting = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_WAITING,
        ]
        self._msg_cancelling = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_CANCELLING,
        ]
        self._msg_generating_library = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_GENERATING_LIBRARY,
        ]
        self._msg_completed = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_RECONSTRUCTION_COMPLETED,
        ]
        self._msg_error = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_ERROR,
        ]
        self._msg_cancelled = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.MESSAGE,
            ConverterElements.STATUS_CANCELLED,
        ]
        self._tpl_progress = language_manager[
            Page.MAIN,
            Panel.CONVERTER,
            TextType.TEMPLATE,
            ConverterElements.PROGRESS_TEMPLATE,
        ]
        self._tpl_eta = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.TIME_ESTIMATION,
        ]

        self._phase: ConversionPhase = ConversionPhase.IDLE
        self._input_path: Optional[Path] = None
        self._output_path: Optional[Path] = None
        self._is_file: bool = True
        self._system_progress = SystemProgress()

        self._service.subscribe(self._on_service_result)

        self.on_view_changed: Optional[Callable[[ConverterViewModel], None]] = None
        self.on_success: Optional[VoidCallback] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_no_files_to_process: Optional[VoidCallback] = None
        self.on_no_generators: Optional[VoidCallback] = None
        self.on_load_file: Optional[PathCallback] = None
        self.on_load_directory: Optional[VoidCallback] = None
        self.on_cancelled: Optional[VoidCallback] = None
        self.generate_library: Optional[VoidCallback] = None
        self.cancel_library_generation: Optional[VoidCallback] = None
        self.is_library_available: Optional[Callable[[], bool]] = None

    def is_running(self) -> bool:
        return self._service.is_running()

    def emit_initial_view(self) -> None:
        self._emit_view_model(self._msg_idle, 0.0, "0%")

    def set_input_path(self, input_path: Path, convert: bool = False) -> None:
        config = self._config_manager.config.model_copy()
        if not self._assign_paths(input_path, config):
            return

        if not self.is_running():
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(self._msg_idle, 0.0, "0%")

        if convert:
            self.start_conversion()

    def start_conversion(self) -> None:
        if self.is_running():
            logger.warning("Conversion is already in progress")
            return

        if not self._config_manager.config.generation.generators:
            self.call(self.on_no_generators)
            return

        self._phase = ConversionPhase.WAITING
        self._emit_view_model(self._msg_waiting, 0.0, "0%")
        self.call(self.generate_library)
        self._wait_for_library_and_start()

    def cancel(self) -> None:
        if self._service.is_running():
            self._phase = ConversionPhase.CANCELLING
            self._emit_view_model(self._msg_cancelling, 0.0, "0%")
            self._system_progress.error()
            self._service.cancel()
        elif self._phase == ConversionPhase.WAITING:
            self.call(self.cancel_library_generation)
            self._on_cancellation_complete()

    def close(self) -> None:
        try:
            self._service.cleanup()
        finally:
            self._system_progress.clear()
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(self._msg_idle, 0.0, "0%")

    def handle_load_request(self) -> None:
        if self._is_file:
            if self._output_path:
                self.call(self.on_load_file, self._output_path)
        else:
            self.call(self.on_load_directory)

        self.close()

    def cleanup(self) -> None:
        self._service.cleanup()
        self._system_progress.clear()

    def _on_service_result(self, result: ConversionResult) -> None:
        match result:
            case ServiceStarted(total=total):
                self._system_progress.start(total)
            case ServiceProgress() as progress:
                self._handle_progress_result(progress)
            case ServiceIntermediate(data=progress):
                self._handle_library_progress(progress)
            case ServiceSuccess(value=output_path):
                self._on_conversion_complete(output_path)
            case ServiceError(exception=exception):
                self._on_conversion_error(exception)
            case ServiceCancelled():
                self._on_cancellation_complete()

    def _handle_progress_result(self, progress: ServiceProgress[Path]) -> None:
        if self._phase == ConversionPhase.CANCELLING:
            total = max(progress.total, 1)
            self._emit_view_model(
                self._msg_cancelling,
                progress.completed / total,
                "0%",
            )
            return

        self._phase = ConversionPhase.RUNNING
        self._system_progress.set(progress.completed, progress.total)
        eta_string = ETAEstimator.format_duration(progress.eta_seconds)
        total = max(progress.total, 1)
        percent_string = f"{min(100, int(progress.completed * 100 / total))}%"
        status_text = self._tpl_progress.format(progress.completed, progress.total)

        if eta_string:
            status_text += self._tpl_eta.format(eta_string=eta_string)

        display_input_path = (
            to_path(str(progress.current_item)) if progress.current_item is not None else self._input_path
        )
        self._emit_view_model(
            status_text,
            progress.completed / total,
            percent_string,
            input_path=display_input_path,
        )

    def _handle_library_progress(self, progress: TaskProgress) -> None:
        if self._phase != ConversionPhase.WAITING:
            return
        total = max(progress.total, 1)
        fraction = progress.completed / total
        self._emit_view_model(self._msg_generating_library, fraction, f"{int(fraction * 100)}%")

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
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logger.error("Failed to determine output path")
            self.call(self.on_error, exception)
            return False
        return True

    def _wait_for_library_and_start(self) -> None:
        if self._phase != ConversionPhase.WAITING:
            return

        if not self.call(self.is_library_available):
            self._emit_view_model(self._msg_generating_library, 0.0, "0%")
            CallbackQueue.add(
                self._wait_for_library_and_start,
                priority=self._scheduling.priority_schedule,
                delay=self._scheduling.delay_schedule,
            )
        else:
            self._start_conversion()

    def _start_conversion(self) -> None:
        assert self._input_path is not None, "Input path is not set"
        config = self._config_manager.config.model_copy()
        self._service.start(config, self._input_path)
        self._system_progress.initialize()

    def _on_conversion_complete(self, output_path: Path) -> None:
        if output_path.exists():
            self._output_path = output_path

        self._phase = ConversionPhase.COMPLETED
        self._emit_view_model(self._msg_completed, 1.0, "100%")
        self.call(self.on_success)

    def _on_conversion_error(self, exception: Exception) -> None:
        self._system_progress.error()
        self._phase = ConversionPhase.FAILED
        self._emit_view_model(self._msg_error, 0.0, "100%")
        if isinstance(exception, NoFilesToProcessError):
            self.call(self.on_no_files_to_process)
        else:
            self.call(self.on_error, exception)

    def _on_cancellation_complete(self) -> None:
        self._phase = ConversionPhase.CANCELLED
        self._emit_view_model(self._msg_cancelled, 0.0, "100%")
        CallbackQueue.add(
            self.close,
            priority=self._scheduling.priority_schedule,
            delay=self._scheduling.delay_cancel,
        )
        self.call(self.on_cancelled)

    def _emit_view_model(
        self,
        status_text: str,
        progress: float,
        progress_overlay: str,
        input_path: Optional[Path] = None,
    ) -> None:
        display_output = (
            self._output_path if self._output_path is not None else self._config_manager.get_reconstructions_directory()
        )
        view_model = ConverterViewModel(
            phase=self._phase,
            status_text=status_text,
            progress=progress,
            progress_overlay=progress_overlay,
            input_path=(input_path if input_path is not None else self._input_path),
            output_path=display_output,
            is_file=self._is_file,
        )
        self.call(self.on_view_changed, view_model)
