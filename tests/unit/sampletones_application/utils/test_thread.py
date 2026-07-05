import gc
import threading
from typing import Dict

from sampletones_application.utils.thread import SingleThreadExecutor

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
