import gc
import tracemalloc
from typing import Callable


def retained_bytes(work: Callable[[], object]) -> int:
    """The bytes the work leaves allocated once the collector has run, its answer included.

    Tracing starts with the work, so what is counted is what the work built and something still
    reaches: the answer it returns, and whatever it stored in what lived before it ran.
    """
    gc.collect()
    tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        answer = work()
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    del answer
    return after - before
