import gc
import threading
from typing import Dict, List
from unittest.mock import patch

from sampletones_application.utils.parallelization.thread import (
    BackgroundWorkCancelled,
    SingleThreadExecutor,
    concurrent,
)

JOIN_TIMEOUT: float = 5.0
DEADLINE_TIMEOUT: float = 0.05


class TestJoinAll:
    def test_waits_for_worker_of_a_collected_executor(self) -> None:
        """A worker must stay joinable for its whole lifetime, including after its
        owning executor has been garbage collected. A worker escaping the join and
        touching torn-down resources (e.g. the dearpygui context) crashes the
        process, so quiescence here is a hard safety contract.
        """
        started = threading.Event()
        release = threading.Event()
        worker_holder: Dict[str, threading.Thread] = {}

        def task() -> None:
            worker_holder["thread"] = threading.current_thread()
            started.set()
            release.wait()

        executor = SingleThreadExecutor()
        assert executor.execute(task, wait=False)
        assert started.wait(JOIN_TIMEOUT)

        del executor
        gc.collect()

        releaser = threading.Timer(0.1, release.set)
        releaser.start()
        try:
            SingleThreadExecutor.join_all(timeout=JOIN_TIMEOUT)
            worker_alive_after_join = worker_holder["thread"].is_alive()
        finally:
            release.set()
            releaser.cancel()
            releaser.join()

        worker_holder["thread"].join(JOIN_TIMEOUT)
        assert not worker_alive_after_join

    def test_returns_at_the_deadline_while_a_worker_still_runs(self) -> None:
        started = threading.Event()
        release = threading.Event()

        executor = SingleThreadExecutor()
        assert executor.execute(lambda: (started.set(), release.wait()) and None, wait=False)
        assert started.wait(JOIN_TIMEOUT)

        try:
            SingleThreadExecutor.join_all(timeout=DEADLINE_TIMEOUT)
            with executor._lock:
                worker = executor._thread
            assert worker is not None
            assert worker.is_alive()
        finally:
            release.set()

        SingleThreadExecutor.join_all(timeout=JOIN_TIMEOUT)


class TestShutdownCancellation:
    def teardown_method(self) -> None:
        SingleThreadExecutor.reset_shutdown()
        SingleThreadExecutor.join_all(timeout=JOIN_TIMEOUT)

    def test_request_query_and_reset(self) -> None:
        assert not SingleThreadExecutor.is_shutting_down()

        SingleThreadExecutor.request_shutdown()
        assert SingleThreadExecutor.is_shutting_down()

        SingleThreadExecutor.reset_shutdown()
        assert not SingleThreadExecutor.is_shutting_down()

    def test_concurrent_task_is_skipped_while_shutting_down(self) -> None:
        ran: List[bool] = []

        class Worker:
            @concurrent(wait=True)
            def work(self) -> None:
                ran.append(True)

        SingleThreadExecutor.request_shutdown()
        Worker().work()
        SingleThreadExecutor.join_all(timeout=JOIN_TIMEOUT)

        assert ran == []

    def test_cancelled_exception_unwinds_without_logging_an_error(self) -> None:
        class Worker:
            @concurrent(wait=True)
            def work(self) -> None:
                raise BackgroundWorkCancelled

        with patch("sampletones_application.utils.parallelization.thread.logger") as logger:
            Worker().work()
            SingleThreadExecutor.join_all(timeout=JOIN_TIMEOUT)

        logger.error_with_traceback.assert_not_called()


class TestExecute:
    def test_skips_a_new_task_while_busy_without_wait(self) -> None:
        started = threading.Event()
        release = threading.Event()

        executor = SingleThreadExecutor()
        assert executor.execute(lambda: (started.set(), release.wait()) and None, wait=False)
        assert started.wait(JOIN_TIMEOUT)

        try:
            assert not executor.execute(lambda: None, wait=False)
        finally:
            release.set()

        SingleThreadExecutor.join_all(timeout=JOIN_TIMEOUT)
