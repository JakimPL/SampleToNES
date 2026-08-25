import threading
from typing import Callable, Final

from sampletones_core.parallelization.channel.protocol import ProgressChannel
from sampletones_core.parallelization.task import TaskReport
from sampletones_shared.logger import LoggerProtocol
from sampletones_shared.types.callback import VoidCallback

POLL_SECONDS: Final[float] = 0.05
DRAIN_SECONDS: Final[float] = 0.0
JOIN_SECONDS: Final[float] = 1.0
PUMP_THREAD_NAME: Final[str] = "TaskProcessorProgress"


class ProgressPump:
    """Carries what the tasks report to whoever is watching the run.

    A run's monitor thread waits on the results the pool hands back, so a report arriving between
    two of them is heard on a thread of its own. Everything already waiting is taken in one turn
    and announced once, which holds the announcements to the rate this reads at however many steps
    the tasks file in between — the reading a bar wants, at a rate a bar can be redrawn at.
    """

    def __init__(
        self,
        channel: ProgressChannel,
        *,
        record: Callable[[TaskReport], None],
        announce: VoidCallback,
        logger: LoggerProtocol,
    ) -> None:
        """Holds the one thread that reads a channel.

        Args:
            channel: The line the tasks report on.
            record: Takes each report as where the task that filed it now stands.
            announce: Tells whoever is watching that the run has moved.
            logger: Hears a channel that ends before the pump is asked to stop.
        """
        self._channel = channel
        self._record = record
        self._announce = announce
        self._logger = logger
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._read, daemon=True, name=PUMP_THREAD_NAME)

    def start(self) -> None:
        """Begins reading the channel."""
        self._thread.start()

    def stop(self) -> None:
        """Asks the reading to end, and waits for the thread to leave the channel alone."""
        self._stopped.set()
        if self._thread.is_alive():
            self._thread.join(timeout=JOIN_SECONDS)

    def _read(self) -> None:
        while not self._stopped.is_set():
            try:
                report = self._channel.poll(POLL_SECONDS)
                if report is None:
                    continue

                self._record(report)
                self._drain()
            except (EOFError, OSError) as exception:
                self._logger.warning(f"Progress channel ended while the run was still reading: {exception}")
                return

            self._announce()

    def _drain(self) -> None:
        """Takes every report already waiting, so one turn of the loop announces them together."""
        while (report := self._channel.poll(DRAIN_SECONDS)) is not None:
            self._record(report)
