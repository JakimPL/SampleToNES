import threading
from typing import Optional

import pytest

from sampletones_application.services.regeneration.jobs import (
    ListeningJob,
    RenderJob,
)
from sampletones_application.services.regeneration.service import (
    RegenerationService,
)
from sampletones_application.services.result import ServiceError


class RegenerationHold:
    """Holds every rebuild of an edited channel on its worker before it computes, until the scenario releases
    it.

    The rebuild waits where the real one runs, so the application draws and answers while the edit
    is on its way, and once released the real rebuild computes the edit's result. A rendering of
    what the reader hears, which the same worker runs on opening a document and on a box ticked,
    goes through at once, so the document stands drawn while the rebuilds wait; a voice's preview
    in the sequencer is a listening on a worker of its own and passes through the same way. The hold lets
    every rebuild through from its release on, until the scenario holds again. A scenario standing
    for a rebuild that breaks lets the held rebuilds go as that failure instead, which the service
    reports the way it reports a rebuild that raised.
    """

    def __init__(self) -> None:
        self._released = threading.Event()
        self._lock = threading.Lock()
        self._waiting = 0
        self._failure: Optional[Exception] = None

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Replaces the service's rebuild with one that waits for the release before it computes."""
        run = RegenerationService._run  # pylint: disable=protected-access

        def held(service: RegenerationService, job: RenderJob) -> None:
            if isinstance(job, ListeningJob):
                run(service, job)
                return

            self._wait()
            if self._failure is not None:
                service._emit(ServiceError(exception=self._failure))  # pylint: disable=protected-access
                return

            run(service, job)

        monkeypatch.setattr(RegenerationService, "_run", held)

    def waiting(self) -> int:
        """How many rebuilds stand held."""
        with self._lock:
            return self._waiting

    def release(self) -> None:
        """Lets every held rebuild, and every one asked for later, carry on."""
        self._released.set()

    def hold_again(self) -> None:
        """Holds every rebuild asked for from now on, as the hold did before its release."""
        self._released.clear()

    def fail(self, failure: Exception) -> None:
        """Lets every held rebuild, and every one asked for after, go as ``failure``."""
        self._failure = failure
        self._released.set()

    def _wait(self) -> None:
        with self._lock:
            self._waiting += 1

        self._released.wait()
        with self._lock:
            self._waiting -= 1
