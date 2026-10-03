import itertools
import threading
from typing import Callable, Final

import pytest

from sampletones_application.services.export.reporter import ExportProgressReporter
from sampletones_application.services.result import ServiceProgress
from sampletones_core.exports.stage import ExportStage
from tests.suite.screens.holds.constants import RELEASE_POLL_SECONDS

FIRST_REPORT: Final[int] = 0


class ExportHold:
    """Holds every export at one report of its stages, until the scenario releases it.

    A run reports each stage it reaches and then asks whether it is still wanted. The hold answers
    that question at the report it stands at, once the export's window has heard the stage, so the
    window shows the run under way. While held, the run still hears a cancel and unwinds the way a
    cancel unwinds a real run. Released, every run goes on to its end until the scenario holds again.
    """

    def __init__(self) -> None:
        self._released = threading.Event()
        self._lock = threading.Lock()
        self._waiting = 0
        self._held_report = FIRST_REPORT

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wraps the export reporter so each run asks its question through the hold."""
        build = ExportProgressReporter.__init__

        def held(
            reporter: ExportProgressReporter,
            emit: Callable[[ServiceProgress[ExportStage]], None],
            withdrawn: Callable[[], bool],
        ) -> None:
            build(reporter, emit, self._gate(withdrawn))

        monkeypatch.setattr(ExportProgressReporter, "__init__", held)

    def waiting(self) -> int:
        """How many runs stand held."""
        with self._lock:
            return self._waiting

    def release(self) -> None:
        """Lets every held run, and every one that starts later, go on to its end."""
        self._released.set()

    def hold_at(self, report: int) -> None:
        """Holds every run from now on at its report numbered ``report``, counted from 0.

        The earlier reports pass.
        """
        self._held_report = report
        self._released.clear()

    def _gate(self, withdrawn: Callable[[], bool]) -> Callable[[], bool]:
        """The question one run asks after each report; it waits at the held report until released or
        withdrawn.
        """
        reports = itertools.count()

        def asked() -> bool:
            if next(reports) == self._held_report:
                self._wait(withdrawn)

            return withdrawn()

        return asked

    def _wait(self, withdrawn: Callable[[], bool]) -> None:
        with self._lock:
            self._waiting += 1

        while not self._released.wait(RELEASE_POLL_SECONDS) and not withdrawn():
            continue

        with self._lock:
            self._waiting -= 1
