from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final, Optional, Protocol, Tuple

from sampletones_application.logic.main.converter.messages import ConverterMessages
from sampletones_application.services.conversion.result import ConversionItem, ConversionResult
from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_application.utils.progress import SystemProgress
from sampletones_application.view_model.main.converter import ACTIVE_PHASES, ConversionPhase
from sampletones_core.configs import Config
from sampletones_core.parallelization import TaskProgress
from sampletones_core.reconstructions.converter import ConversionPlan
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin

SYSTEM_PROGRESS_STEPS: Final[int] = 1000


@dataclass(frozen=True)
class ConversionSuccess:
    """The outcome a completed conversion hands to its listener: the reconstructions it wrote.

    One written reconstruction is one the reader can open straight away; several are a batch,
    which the reader reaches as a folder."""

    written: Tuple[Path, ...]

    @property
    def is_single(self) -> bool:
        """One reconstruction was written, so it is the one a follow-up offer would load."""
        return len(self.written) == 1


@dataclass(frozen=True)
class RunReport:
    """Where a run stands, in the words a reader watching it reads.

    ``input_path`` names the recording under way, which a batch changes as it goes; a run naming
    none leaves the reader looking at what they picked.
    """

    status_text: str
    progress: float
    input_path: Optional[Path]


class ConversionServiceProtocol(Protocol):
    """The slice of the conversion service a run drives.

    Typing the collaborator structurally keeps the logic layer bound to the
    service's result contract alone; the composition root supplies the real
    service.
    """

    def subscribe(self, handler: Callable[[ConversionResult], None]) -> None: ...

    def start(self, config: Config, plan: ConversionPlan) -> None: ...

    def cancel(self) -> None: ...

    def cleanup(self) -> None: ...

    def shutdown(self) -> None: ...

    def is_running(self) -> bool: ...


class ConversionRun(CallbackMixin):
    """One conversion from the moment it is requested to the moment it is closed.

    The run owns the phase, the service driving it and the taskbar progress that follows it, and
    reports where it stands after every step it takes. What it converts is settled before it
    starts: a run takes a plan and the name of the document it is writing, and answers only for
    what happens to them.
    """

    def __init__(
        self,
        conversion_service: ConversionServiceProtocol,
        *,
        messages: ConverterMessages,
    ) -> None:
        self._service = conversion_service
        self._messages = messages
        self._system_progress = SystemProgress()
        self._phase: ConversionPhase = ConversionPhase.IDLE
        self._written: Tuple[Path, ...] = ()
        self._reconstruction_name: str = ""

        self._service.subscribe(self._on_service_result)

        self.on_report: Optional[Callable[[RunReport], None]] = None
        self.on_success: Optional[Callable[[ConversionSuccess], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_canceled: Optional[VoidCallback] = None

    @property
    def phase(self) -> ConversionPhase:
        return self._phase

    @property
    def is_active(self) -> bool:
        """A conversion is occupying resources from the moment of request (the WAITING phase, during
        which the library is prepared and the run is scheduled) until it reaches a terminal phase."""
        return self._phase in ACTIVE_PHASES

    @property
    def is_running(self) -> bool:
        """The service holds the run, so canceling it is the service's business."""
        return self._service.is_running()

    @property
    def written(self) -> Tuple[Path, ...]:
        """The reconstructions the last completed run wrote."""
        return self._written

    def wait(self) -> None:
        """Takes up a request, while the library it converts against is prepared."""
        self._phase = ConversionPhase.WAITING
        self._report(self._messages.waiting, 0.0)

    def begin(self, config: Config, plan: ConversionPlan, reconstruction_name: str) -> None:
        """Hands the plan to the service, which is where the conversion itself starts."""
        self._reconstruction_name = reconstruction_name
        self._system_progress.initialize()
        self._service.start(config, plan)

    def cancel(self) -> None:
        """Asks the service to give up the run it holds."""
        self._phase = ConversionPhase.CANCELING
        self._report(self._messages.canceling, 0.0)
        self._system_progress.error()
        self._service.cancel()

    def abandon(self) -> None:
        """Gives up a request still standing this side of the service, which cancels it all the same."""
        self._settle_as_canceled()

    def close(self) -> None:
        """Lets the run go, whatever it came to, and returns to idle."""
        try:
            self._service.cleanup()
        finally:
            self._system_progress.clear()
            self._written = ()
            self.return_to_idle()

    def return_to_idle(self) -> None:
        """Marks a settled run as done with, so the panel offers to convert again."""
        self._phase = ConversionPhase.IDLE

    def cleanup(self) -> None:
        """Shuts the service down, which is the end of every run this object could hold."""
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
            case ServiceSuccess(value=written):
                self._settle_as_complete(written)
            case ServiceError(exception=exception):
                self._settle_as_failed(exception)
            case ServiceCanceled():
                self._settle_as_canceled()

    def _handle_progress_result(self, progress: ServiceProgress[ConversionItem]) -> None:
        if self._phase == ConversionPhase.CANCELING:
            self._report(self._messages.canceling, progress.fraction)
            return

        self._phase = ConversionPhase.RUNNING
        self._system_progress.set(
            round(progress.fraction * SYSTEM_PROGRESS_STEPS),
            SYSTEM_PROGRESS_STEPS,
        )
        self._report(
            self._messages.progress_text(progress, self._reconstruction_name),
            progress.fraction,
            input_path=self._item_path(progress),
        )

    def _item_path(self, progress: ServiceProgress[ConversionItem]) -> Optional[Path]:
        """The recording the run names itself by, where one is under way."""
        return progress.current_item.source if progress.current_item is not None else None

    def _handle_library_progress(self, progress: TaskProgress) -> None:
        if self._phase != ConversionPhase.WAITING:
            return

        total = max(progress.total, 1)
        self._report(self._messages.generating_library, progress.completed / total)

    def _settle_as_complete(self, written: Tuple[Path, ...]) -> None:
        """Settles a finished run, telling its listener what was written before reporting.

        The reconstruction a run wrote is what a reader is then looking at, so the listener takes
        it up first and the report that follows names it.
        """
        self._written = written
        self._phase = ConversionPhase.COMPLETED
        self.call(self.on_success, ConversionSuccess(written=written))
        self._report(self._messages.completed, 1.0)

    def _settle_as_failed(self, exception: Exception) -> None:
        self._system_progress.error()
        self._phase = ConversionPhase.FAILED
        self._report(self._messages.failed, 0.0)
        self.call(self.on_error, exception)

    def _settle_as_canceled(self) -> None:
        self._phase = ConversionPhase.CANCELED
        self._report(self._messages.canceled, 0.0)
        self.call(self.on_canceled)

    def _report(
        self,
        status_text: str,
        progress: float,
        input_path: Optional[Path] = None,
    ) -> None:
        self.call(
            self.on_report,
            RunReport(status_text=status_text, progress=progress, input_path=input_path),
        )
