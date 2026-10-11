import gc
import sys
import threading
from functools import partial
from pathlib import Path
from typing import Callable, Final, Iterator, List

import numpy as np
import pytest

from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from tests.suite.stems import SHARED_CHANNEL, taking_turns_reconstruction

JOIN_TIMEOUT: Final[float] = 10.0
SWITCH_INTERVAL: Final[float] = 1e-5
REPEATS: Final[int] = 5
READERS: Final[int] = 3
WRITERS: Final[int] = 2
ROUNDS: Final[int] = 30
KEPT_RENDERS: Final[int] = 3
WRITER_SPACING: Final[int] = 1000


def _document(index: int) -> Reconstruction:
    """A small document of its own, which no other document shares a stream with."""
    return taking_turns_reconstruction((Path(f"{index}-a.wav"), Path(f"{index}-b.wav"))).detached()


@pytest.fixture(name="switching_often")
def switching_often_fixture() -> Iterator[None]:
    """The interpreter handing the lock over every few microseconds, so the threads meet in more places."""
    interval = sys.getswitchinterval()
    sys.setswitchinterval(SWITCH_INTERVAL)
    yield
    sys.setswitchinterval(interval)


@pytest.fixture(name="thread_failures")
def thread_failures_fixture(monkeypatch: pytest.MonkeyPatch) -> List[BaseException]:
    """What a thread of the case raised and left unhandled, which the case reads once every thread has ended."""
    failures: List[BaseException] = []
    monkeypatch.setattr(threading, "excepthook", lambda args: failures.append(args.exc_value))
    return failures


def _run_together(workers: List[Callable[[], None]]) -> None:
    """Runs every worker on a thread of its own and waits for all of them.

    Raises:
        AssertionError: If a worker is still running once the join's time has run, which is what a
            deadlock on the cache's lock looks like.
    """
    threads = [threading.Thread(target=work, name=f"RenderCaseWorker-{index}") for index, work in enumerate(workers)]
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(JOIN_TIMEOUT)

    assert not any(thread.is_alive() for thread in threads), "a worker never finished"


def _reads(renders: RenderCache, shared: Reconstruction) -> None:
    """Reads the shared document's renders over and over, adopting them again wherever the writers evicted them."""
    expected = rendered_channels(shared)
    expected_mix = rendered_mix(shared)
    for _ in range(ROUNDS):
        held = renders.held(shared)
        if held.keys() != expected.keys():
            renders.adopt(shared, expected, expected_mix)
            held = renders.held(shared)

        assert all(np.array_equal(held[name], expected[name]) for name in held)


def _writes(renders: RenderCache, offset: int) -> None:
    for turn in range(ROUNDS):
        document = _document(offset + turn)
        renders.adopt(document, rendered_channels(document), rendered_mix(document))


class TestReadersAndWritersSharingOneCache:
    """Readers on several threads read whole renders while writers fill the cache past its budget and let
    their documents go.

    The budget holds a few renders, so the writers evict what the readers keep reading, and each
    writer's documents die as it moves on, so their renders are forgotten from the writers' threads.
    Every read answers with the render the document sounds, and once every document has gone the
    cache keeps nothing and counts nothing.
    """

    @pytest.mark.parametrize("repeat", range(REPEATS))
    def test_every_read_is_whole_and_the_accounts_balance(
        self,
        repeat: int,
        switching_often: None,
        thread_failures: List[BaseException],
    ) -> None:
        shared = _document(0)
        budget = KEPT_RENDERS * rendered_channels(shared)[SHARED_CHANNEL].nbytes
        renders = RenderCache(budget_bytes=budget)

        _run_together(
            [partial(_reads, renders, shared)] * READERS
            + [partial(_writes, renders, WRITER_SPACING * (writer + 1)) for writer in range(WRITERS)]
        )

        assert thread_failures == []
        assert renders.held_bytes <= budget
        del shared
        gc.collect()
        assert renders.held_bytes == 0


class TestADocumentLetGoWhileItsRenderIsMade:
    """A document let go of everywhere else stays with the thread making and adopting its render, and its
    render leaves once that thread lets go.

    The maker's own reference keeps the streams alive through the render and the keep, so the
    render is kept under a live identity; the forgetting then runs as the maker's references die.
    """

    def test_the_render_leaves_once_the_maker_lets_go(
        self,
        renders: RenderCache,
        thread_failures: List[BaseException],
    ) -> None:
        rendered = threading.Event()
        release = threading.Event()

        def make_and_adopt() -> None:
            document = _document(0)
            channels = rendered_channels(document)
            mixed = rendered_mix(document)
            rendered.set()
            assert release.wait(JOIN_TIMEOUT)
            renders.adopt(document, channels, mixed)

        maker = threading.Thread(target=make_and_adopt, name="RenderCaseMaker")
        maker.start()
        assert rendered.wait(JOIN_TIMEOUT)
        gc.collect()

        release.set()
        maker.join(JOIN_TIMEOUT)

        assert not maker.is_alive()
        assert thread_failures == []
        gc.collect()
        assert renders.held_bytes == 0
