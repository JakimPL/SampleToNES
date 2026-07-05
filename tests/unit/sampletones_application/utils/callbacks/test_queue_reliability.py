import threading
from typing import List
from unittest.mock import patch

import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue

_real_queue_add = CallbackQueue.add


@pytest.fixture(autouse=True)
def real_queue():
    """Run a real CallbackQueue worker for this test.

    CallbackQueue is a process-global singleton, so a prior test in the same
    process may leave a worker alive or tasks pending. We stop() first to halt
    and join any leaked worker and clear the queue, then start() a fresh one;
    teardown stops it again.
    """
    with patch.object(CallbackQueue, "add", _real_queue_add):
        CallbackQueue.stop()
        CallbackQueue.start()
        yield
        CallbackQueue.stop()


class TestCallbackQueueDelivery:
    def test_callback_is_delivered_while_worker_is_running(self) -> None:
        fired = threading.Event()

        def callback() -> None:
            fired.set()

        CallbackQueue.add(callback)
        CallbackQueue.notify_frame()

        assert fired.wait(timeout=0.5), "Callback was not delivered within 500 ms"

    def test_multiple_callbacks_all_delivered(self) -> None:
        results: List[int] = []
        done = threading.Event()

        def make_callback(value: int):
            def callback() -> None:
                results.append(value)
                if len(results) == 3:
                    done.set()

            return callback

        CallbackQueue.add(make_callback(1))
        CallbackQueue.add(make_callback(2))
        CallbackQueue.add(make_callback(3))
        CallbackQueue.notify_frame()

        assert done.wait(timeout=0.5), "Not all callbacks were delivered within 500 ms"
        assert sorted(results) == [1, 2, 3]

    def test_stop_drops_pending_callbacks(self) -> None:
        """Callbacks added with delay=1 are dropped when stop() is called before
        notify_frame() advances the counter.

        This documents the known risk: application shutdown while service results
        are in-flight silently discards those results.
        """
        fired = threading.Event()

        def callback() -> None:
            fired.set()

        CallbackQueue.add(callback, delay=1)
        CallbackQueue.stop()

        assert not fired.wait(timeout=0.1), "Callback should have been dropped by stop()"

    def test_exception_in_callback_does_not_kill_worker(self) -> None:
        """An Exception raised inside a callback is caught and logged; the worker
        continues processing subsequent callbacks.
        """
        good_fired = threading.Event()

        def bad_callback() -> None:
            raise RuntimeError("intentional error")

        def good_callback() -> None:
            good_fired.set()

        CallbackQueue.add(bad_callback)
        CallbackQueue.add(good_callback)
        CallbackQueue.notify_frame()

        assert good_fired.wait(timeout=0.5), "Worker should have survived the bad callback"

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
    def test_base_exception_in_callback_kills_worker(self) -> None:
        """A BaseException (e.g. SystemExit) raised in a callback is NOT caught by
        CallbackQueue.run(), which only handles Exception.  The worker thread dies
        and subsequent callbacks are never processed.

        This documents a known gap: a non-Exception BaseException in any callback
        silently kills the queue for the remainder of the application's lifetime.
        Note: SystemExit in a background thread kills only that thread, not the process.
        """
        good_fired = threading.Event()

        def base_exception_callback() -> None:
            raise SystemExit(0)

        def good_callback() -> None:
            good_fired.set()

        CallbackQueue.add(base_exception_callback)
        CallbackQueue.add(good_callback)
        CallbackQueue.notify_frame()

        assert not good_fired.wait(timeout=0.3), "Worker should have been killed by BaseException"


class TestCallbackQueueFrameDelay:
    def test_callback_with_delay_does_not_fire_without_frame_tick(self) -> None:
        fired = threading.Event()

        def callback() -> None:
            fired.set()

        CallbackQueue.add(callback, delay=1)

        assert not fired.wait(timeout=0.05), "Callback fired before its frame was reached"

    def test_callback_with_delay_fires_after_frame_tick(self) -> None:
        fired = threading.Event()

        def callback() -> None:
            fired.set()

        CallbackQueue.add(callback, delay=1)
        CallbackQueue.notify_frame()

        assert fired.wait(timeout=0.5), "Callback did not fire after frame tick"

    def test_zero_delay_callback_fires_without_extra_tick(self) -> None:
        fired = threading.Event()

        def callback() -> None:
            fired.set()

        CallbackQueue.add(callback, delay=0)
        CallbackQueue.notify_frame()

        assert fired.wait(timeout=0.5)
