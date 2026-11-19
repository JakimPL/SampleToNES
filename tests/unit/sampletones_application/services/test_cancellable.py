import threading
from typing import Final, Iterator, List
from unittest.mock import patch

import pytest

from sampletones_application.services.cancellable import CancellableJobService

WAIT_SECONDS: Final[float] = 10.0


class HeldJobService(CancellableJobService[int]):
    """A service whose job waits until the case lets it go, and records whether it saw a cancel."""

    def __init__(self) -> None:
        super().__init__(priority=0)
        self.started = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()
        self.saw_cancel: List[bool] = []

    def run_held(self) -> bool:
        return self._start_job(self._held)

    def _held(self) -> None:
        self.started.set()
        self.release.wait(WAIT_SECONDS)
        self.saw_cancel.append(self._cancel_event.is_set())
        self.finished.set()

    def _failing(self) -> None:
        self.started.set()
        raise RuntimeError("the job went wrong")


@pytest.fixture(name="synchronous_executor", autouse=True)
def real_executor_fixture() -> Iterator[None]:
    """The real worker thread, since these cases are about a job holding the service while it runs."""
    yield


@pytest.fixture(name="service")
def service_fixture() -> HeldJobService:
    return HeldJobService()


def _wait_until_idle(service: HeldJobService) -> None:
    for _ in range(int(WAIT_SECONDS * 100)):
        if not service.is_running():
            return
        threading.Event().wait(0.01)
    raise AssertionError("the job never ended")


class TestOneJobAtATime:
    """A job holds the service until it ends; a second request meanwhile is declined, a cancel
    reaches the job, and once it ends the service takes the next request."""

    def test_a_job_is_taken_and_holds_the_service(self, service: HeldJobService) -> None:
        assert service.run_held()
        assert service.started.wait(WAIT_SECONDS)
        assert service.is_running()

        assert not service.run_held()

        service.cancel()
        service.release.set()
        assert service.finished.wait(WAIT_SECONDS)
        _wait_until_idle(service)
        assert service.saw_cancel == [True]

        service.started.clear()
        service.release.set()
        assert service.run_held()
        assert service.started.wait(WAIT_SECONDS)
        _wait_until_idle(service)
        assert service.saw_cancel == [True, False]


class TestTheRunningFlagFollowsTheJob:
    def test_a_job_that_fails_leaves_the_service_free(self, service: HeldJobService) -> None:
        """A job is a service's own code, which catches its failures; one that escapes still frees it."""
        service._running.set()

        with pytest.raises(RuntimeError):
            service._run_to_its_end(service._failing)

        assert not service.is_running()
        service.release.set()
        assert service.run_held()

    def test_a_job_the_worker_refuses_leaves_the_service_free(self, service: HeldJobService) -> None:
        with patch.object(service._executor, "execute", return_value=False):
            assert not service.run_held()

        assert not service.is_running()

    def test_shutting_down_asks_the_running_job_to_stop(self, service: HeldJobService) -> None:
        assert service.run_held()
        assert service.started.wait(WAIT_SECONDS)

        service.shutdown()
        service.release.set()
        assert service.finished.wait(WAIT_SECONDS)
        assert service.saw_cancel == [True]
