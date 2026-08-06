from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.services.result import (
    ConversionResult,
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
    ACTIVE_PHASES,
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


@dataclass(frozen=True)
class ConversionSuccess:
    """The outcome a completed conversion hands to its listener.

    Carries what the follow-up load offer needs: whether a single file or a
    directory was converted, and where its reconstruction was written."""

    is_file: bool
    output_path: Optional[Path]


class ConversionServiceProtocol(Protocol):
    """The slice of the conversion service the converter logic drives.

    Typing the collaborator structurally keeps the logic layer bound to the
    service's result contract alone; the composition root supplies the real
    service.
    """

    def subscribe(self, handler: Callable[[ConversionResult], None]) -> None: ...

    def start(self, config: Config, input_path: Path) -> None: ...

    def cancel(self) -> None: ...

    def cleanup(self) -> None: ...

    def shutdown(self) -> None: ...

    def is_running(self) -> bool: ...


class ConverterLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        conversion_service: ConversionServiceProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._language_manager = language_manager
        self._config_manager = config_manager
        self._service = conversion_service
        self._scheduling = scheduling
        self._is_operation_active = is_operation_active
        self._msg_idle = language_manager["main.converter.message.status_idle"]
        self._msg_cancelling = language_manager["main.converter.message.status_cancelling"]

        self._phase: ConversionPhase = ConversionPhase.IDLE
        self._input_path: Optional[Path] = None
        self._output_path: Optional[Path] = None
        self._is_file: bool = True
        self._system_progress = SystemProgress()

        self._service.subscribe(self._on_service_result)

        self.on_view_changed: Optional[Callable[[ConverterViewModel], None]] = None
        self.on_success: Optional[Callable[[ConversionSuccess], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_no_files_to_process: Optional[VoidCallback] = None
        self.on_no_generators: Optional[VoidCallback] = None
        self.on_load_file: Optional[PathCallback] = None
        self.on_load_directory: Optional[VoidCallback] = None
        self.on_cancelled: Optional[VoidCallback] = None
        self.generate_library: Optional[VoidCallback] = None
        self.cancel_library_generation: Optional[VoidCallback] = None
        self.is_library_available: Optional[Callable[[], bool]] = None

    @property
    def is_active(self) -> bool:
        """A conversion is occupying resources from the moment of request (the WAITING phase, during
        which the library is prepared and the run is scheduled) until it reaches a terminal phase."""
        return self._phase in ACTIVE_PHASES

    def emit_initial_view(self) -> None:
        self._emit_view_model(self._msg_idle, 0.0)

    def refresh_view(self) -> None:
        """Re-emits the idle view so the Convert button reflects whether another exclusive operation
        is active. Only the idle phase carries the Convert button; the other phases disable it by
        phase alone, so re-emitting them would add nothing."""
        if self._phase == ConversionPhase.IDLE:
            self._emit_view_model(self._msg_idle, 0.0)

    def set_input_path(self, input_path: Path, convert: bool = False) -> None:
        config = self._config_manager.config.model_copy()
        if not self._assign_paths(input_path, config):
            return

        if not self.is_active:
            self._phase = ConversionPhase.IDLE
            self._emit_view_model(self._msg_idle, 0.0)

        if convert:
            self.start_conversion()

    def start_conversion(self) -> None:
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress")
            return

        if not self._config_manager.config.generation.generators:
            self.call(self.on_no_generators)
            return

        self._phase = ConversionPhase.WAITING
        self._emit_view_model(self._language_manager["main.converter.message.status_waiting"], 0.0)
        self.call(self.generate_library)
        self._wait_for_library_and_start()

    def cancel(self) -> None:
        if self._service.is_running():
            self._phase = ConversionPhase.CANCELLING
            self._emit_view_model(self._msg_cancelling, 0.0)
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
            self._emit_view_model(self._msg_idle, 0.0)

    def handle_load_request(self) -> None:
        if self._is_file:
            if self._output_path:
                self.call(self.on_load_file, self._output_path)
        else:
            self.call(self.on_load_directory)

        self.close()

    def cleanup(self) -> None:
        self._service.shutdown()
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
            )
            return

        self._phase = ConversionPhase.RUNNING
        self._system_progress.set(progress.completed, progress.total)
        eta_string = ETAEstimator.format_duration(progress.eta_seconds)
        total = max(progress.total, 1)
        status_text = self._language_manager["main.converter.template.progress_template"].format(
            progress.completed, progress.total
        )

        if eta_string:
            status_text += self._language_manager["global.dialog.template.time_estimation"].format(
                eta_string=eta_string
            )

        display_input_path = (
            to_path(str(progress.current_item)) if progress.current_item is not None else self._input_path
        )
        self._emit_view_model(
            status_text,
            progress.completed / total,
            input_path=display_input_path,
        )

    def _handle_library_progress(self, progress: TaskProgress) -> None:
        if self._phase != ConversionPhase.WAITING:
            return

        total = max(progress.total, 1)
        fraction = progress.completed / total
        self._emit_view_model(self._language_manager["main.converter.message.status_generating_library"], fraction)

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

        return True

    def _wait_for_library_and_start(self) -> None:
        if self._phase != ConversionPhase.WAITING:
            return

        if not self.call(self.is_library_available):
            CallbackQueue.add(
                self._wait_for_library_and_start,
                priority=self._scheduling.priorities.schedule,
                delay=self._scheduling.delays.schedule,
            )
        else:
            self._start_conversion()

    def _start_conversion(self) -> None:
        assert self._input_path is not None, "Input path is not set"
        config = self._config_manager.config.model_copy()
        self._system_progress.initialize()
        self._service.start(config, self._input_path)

    def _on_conversion_complete(self, output_path: Path) -> None:
        if output_path.exists():
            self._output_path = output_path

        self._phase = ConversionPhase.COMPLETED
        self._emit_view_model(self._language_manager["main.converter.message.status_reconstruction_completed"], 1.0)
        self.call(
            self.on_success,
            ConversionSuccess(
                is_file=self._is_file,
                output_path=self._output_path,
            ),
        )

    def _on_conversion_error(self, exception: Exception) -> None:
        self._system_progress.error()
        self._phase = ConversionPhase.FAILED
        self._emit_view_model(self._language_manager["main.converter.message.status_error"], 0.0)
        self._schedule_return_to_idle()
        if isinstance(exception, NoFilesToProcessError):
            self.call(self.on_no_files_to_process)
        else:
            self.call(self.on_error, exception)

    def _on_cancellation_complete(self) -> None:
        self._phase = ConversionPhase.CANCELLED
        self._emit_view_model(self._language_manager["main.converter.message.status_cancelled"], 0.0)
        self._schedule_return_to_idle()
        self.call(self.on_cancelled)

    def _schedule_return_to_idle(self) -> None:
        CallbackQueue.add(
            self.close,
            priority=self._scheduling.priorities.schedule,
            delay=self._scheduling.delays.cancel,
        )

    def _compose_action_label(self, input_path: Optional[Path]) -> str:
        """The label the single action button shows: the cancel label while a conversion holds
        resources, otherwise the convert label named after the selected input."""
        if self._phase in ACTIVE_PHASES:
            return self._language_manager["main.converter.label.cancel_button"]

        base = (
            self._language_manager["main.converter.label.convert_sample_button"]
            if self._is_file
            else self._language_manager["main.converter.label.convert_directory_button"]
        )
        if input_path is None:
            return base

        return self._language_manager["main.converter.template.convert_label_template"].format(base, input_path.name)

    def _emit_view_model(
        self,
        status_text: str,
        progress: float,
        input_path: Optional[Path] = None,
    ) -> None:
        display_output = (
            self._output_path if self._output_path is not None else self._config_manager.get_reconstructions_directory()
        )
        display_input = input_path if input_path is not None else self._input_path
        view_model = ConverterViewModel(
            phase=self._phase,
            status_text=status_text,
            action_label=self._compose_action_label(display_input),
            progress=progress,
            input_path=display_input,
            output_path=display_output,
            is_file=self._is_file,
            other_operation_active=self._is_operation_active(),
        )
        self.call(self.on_view_changed, view_model)
