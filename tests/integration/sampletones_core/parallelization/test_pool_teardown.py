import multiprocessing
import threading
from pathlib import Path
from typing import Any, Final, Iterator, List, Tuple

import pytest

from sampletones_core.parallelization import processor
from sampletones_core.parallelization.processor import TaskProcessor
from tests.suite.parallelization import (
    CountingProcessor,
    FailingProcessor,
    ProgressRecorder,
    stands_partway,
)

WORKER_NAME: Final[str] = "pebble_pool_worker"
MONITOR_NAME: Final[str] = "TaskProcessorMonitor"
READING_TIMEOUT: Final[float] = 60.0
POOL_TIMEOUT: Final[float] = 120.0
SEVERAL_TASKS: Final[int] = 3
TWO_WORKERS: Final[int] = 2
RELEASE_NAME: Final[str] = "release"
JOIN: Final[str] = "join"


def _live_workers() -> List[str]:
    return [process.name for process in multiprocessing.active_children() if process.name == WORKER_NAME]


class WorkersAtTheAnnouncement:
    """Writes down which pool workers are alive at the moment a run announces how it ended."""

    def __init__(self) -> None:
        self.seen: List[List[str]] = []
        self.announced = threading.Event()

    def __call__(self, *_arguments: Any) -> None:
        self.seen.append(_live_workers())
        self.announced.set()


class RecordingPool(processor.ProcessPool):
    """A process pool that writes down every call made to end it, and the thread each came from.

    Pebble's own join stops and joins a closed pool again from inside, so only the calls made from
    outside the pool are written down.
    """

    calls: List[Tuple[str, str]] = []

    def __init__(self, *arguments: Any, **keywords: Any) -> None:
        super().__init__(*arguments, **keywords)
        self._depth = 0

    def close(self) -> None:
        self._record("close")
        super().close()

    def stop(self) -> None:
        self._record("stop")
        super().stop()

    def join(self, timeout: Any = None) -> None:
        self._record(JOIN)
        self._depth += 1
        try:
            super().join(timeout)
        finally:
            self._depth -= 1

    def _record(self, call: str) -> None:
        if self._depth == 0:
            RecordingPool.calls.append((call, threading.current_thread().name))


@pytest.fixture
def release_path(tmp_path: Path) -> Path:
    return tmp_path / RELEASE_NAME


@pytest.fixture
def recorded_pool(monkeypatch: pytest.MonkeyPatch) -> Iterator[List[Tuple[str, str]]]:
    RecordingPool.calls = []
    monkeypatch.setattr(processor, "ProcessPool", RecordingPool)
    yield RecordingPool.calls


def _completed_run(release_path: Path, witness: WorkersAtTheAnnouncement) -> TaskProcessor[int]:
    release_path.touch()
    run = CountingProcessor(SEVERAL_TASKS, release_path, max_workers=TWO_WORKERS)
    run.set_callbacks(on_completed=witness)
    run.start()
    return run


def _canceled_run(release_path: Path, witness: WorkersAtTheAnnouncement) -> TaskProcessor[int]:
    recorder = ProgressRecorder()
    run = CountingProcessor(SEVERAL_TASKS, release_path, max_workers=TWO_WORKERS)
    run.set_callbacks(on_progress=recorder, on_canceled=witness)
    run.start()
    assert recorder.wait_for(stands_partway, READING_TIMEOUT)
    run.cancel()
    return run


def _failed_run(release_path: Path, witness: WorkersAtTheAnnouncement) -> TaskProcessor[int]:
    run = FailingProcessor(SEVERAL_TASKS, release_path, max_workers=TWO_WORKERS)
    run.set_callbacks(on_error=witness)
    run.start()
    return run


ENDINGS: Final = pytest.mark.parametrize(
    "ending",
    [_completed_run, _canceled_run, _failed_run],
    ids=["completed", "canceled", "failed"],
)


class TestARunEndsItsPoolBeforeItAnnounces:
    """Whoever hears how a run ended meets a run with no worker left.

    A conversion starts right after its own library generation, and the application exits right
    after a run is let go, so a worker still being reaped when the outcome goes out is a process
    two owners end up waiting on at once.
    """

    @ENDINGS
    def test_no_worker_is_alive_when_the_outcome_goes_out(self, ending: Any, release_path: Path) -> None:
        witness = WorkersAtTheAnnouncement()
        run = ending(release_path, witness)
        try:
            assert witness.announced.wait(POOL_TIMEOUT)
            assert witness.seen == [[]]
        finally:
            release_path.touch(exist_ok=True)
            run.shutdown()

    @ENDINGS
    def test_the_monitor_ends_the_pool_exactly_once(
        self,
        ending: Any,
        release_path: Path,
        recorded_pool: List[Tuple[str, str]],
    ) -> None:
        witness = WorkersAtTheAnnouncement()
        run = ending(release_path, witness)
        try:
            assert witness.announced.wait(POOL_TIMEOUT)
            run.shutdown()

            joins = [thread for call, thread in recorded_pool if call == JOIN]
            assert joins == [MONITOR_NAME]
            assert {thread for _, thread in recorded_pool} == {MONITOR_NAME}
        finally:
            release_path.touch(exist_ok=True)
            run.shutdown()


class TestShuttingARunDown:
    def test_a_run_shut_down_mid_task_has_no_worker_left_on_return(self, release_path: Path) -> None:
        recorder = ProgressRecorder()
        run = CountingProcessor(SEVERAL_TASKS, release_path, max_workers=TWO_WORKERS)
        run.set_callbacks(on_progress=recorder)
        run.start()
        try:
            assert recorder.wait_for(stands_partway, READING_TIMEOUT)

            run.shutdown()

            assert _live_workers() == []
            assert not run.is_running()
        finally:
            release_path.touch(exist_ok=True)
            run.shutdown()
