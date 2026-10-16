import threading
from typing import Final, List

import numpy as np
import pytest

from sampletones_core.audio.output import PrefetchBuffer, Tagged
from tests.suite.audio.ramp import ramp, ramp_indices

CAPACITY: Final[int] = 100
BLOCK: Final[int] = 64
SETTLE_SECONDS: Final[float] = 5.0
HELD_SECONDS: Final[float] = 0.05


def _rows(buffer: PrefetchBuffer[str], lengths: List[int]) -> None:
    """Puts rows of the given lengths, the ramp running on across them, each reporting its own index."""
    start = 0
    for index, length in enumerate(lengths):
        assert buffer.put(ramp(length, start=start), f"row {index}")
        start += length


def _waiting(target: threading.Thread) -> bool:
    """Whether a thread is still waiting a moment after it started, which a call that returned at once is not."""
    target.join(timeout=HELD_SECONDS)
    return target.is_alive()


class TestTakes:
    """A take fills its block across rows, and each row reports with the block holding its last sample."""

    def test_a_take_fills_its_block_across_rows(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        _rows(buffer, [40, 40, 40])
        block = np.zeros(BLOCK, dtype=np.float32)

        taken = buffer.take_into(block)

        assert taken.frames == BLOCK
        np.testing.assert_array_equal(ramp_indices(block), np.arange(BLOCK))
        assert taken.reports == (Tagged(offset=40, report="row 0"),)
        assert buffer.queued == 120 - BLOCK

    def test_the_rows_after_the_end_come_out_short(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        _rows(buffer, [40, 30])
        buffer.end()
        block = np.zeros(BLOCK, dtype=np.float32)

        first = buffer.take_into(block)
        last = buffer.take_into(block)

        assert (first.frames, first.closed) == (BLOCK, False)
        assert first.reports == (Tagged(offset=40, report="row 0"),)
        assert (last.frames, last.closed) == (70 - BLOCK, False)
        assert last.reports == (Tagged(offset=70 - BLOCK, report="row 1"),)
        assert buffer.take_into(block).frames == 0

    def test_a_closed_buffer_answers_closed_and_leaves_the_block(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        _rows(buffer, [40, 40])
        buffer.close()
        block = np.ones(BLOCK, dtype=np.float32)

        taken = buffer.take_into(block)

        assert taken.closed
        assert taken.frames == 0
        np.testing.assert_array_equal(block, np.ones(BLOCK, dtype=np.float32))


class TestBound:
    """The producer waits while the buffer is full, and a row longer than the whole bound still goes in."""

    def test_a_row_longer_than_the_capacity_goes_into_an_empty_buffer(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)

        assert buffer.put(ramp(3 * CAPACITY), "long row")
        assert buffer.queued == 3 * CAPACITY

    def test_a_put_waits_while_the_buffer_is_full_and_goes_in_once_a_take_frees_room(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        _rows(buffer, [CAPACITY])
        producer = threading.Thread(target=buffer.put, args=(ramp(10), "next row"), daemon=True)
        producer.start()

        waiting = _waiting(producer)
        buffer.take_into(np.zeros(BLOCK, dtype=np.float32))
        producer.join(timeout=SETTLE_SECONDS)

        assert waiting
        assert not producer.is_alive()
        assert buffer.queued == CAPACITY - BLOCK + 10

    def test_a_take_waits_for_a_block_and_returns_once_rows_arrive(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        takes: List[int] = []
        writer = threading.Thread(
            target=lambda: takes.append(buffer.take_into(np.zeros(BLOCK, dtype=np.float32)).frames),
            daemon=True,
        )
        writer.start()

        waiting = _waiting(writer)
        _rows(buffer, [BLOCK])
        writer.join(timeout=SETTLE_SECONDS)

        assert waiting
        assert takes == [BLOCK]


class TestClose:
    """Closing wakes a waiting producer and a waiting writer at once."""

    def test_closing_wakes_a_waiting_producer(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        _rows(buffer, [CAPACITY])
        answers: List[bool] = []
        producer = threading.Thread(target=lambda: answers.append(buffer.put(ramp(10), "row")), daemon=True)
        producer.start()

        waiting = _waiting(producer)
        buffer.close()
        producer.join(timeout=SETTLE_SECONDS)

        assert waiting
        assert answers == [False]

    def test_closing_wakes_a_waiting_writer(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        answers: List[bool] = []
        writer = threading.Thread(
            target=lambda: answers.append(buffer.take_into(np.zeros(BLOCK, dtype=np.float32)).closed),
            daemon=True,
        )
        writer.start()

        waiting = _waiting(writer)
        buffer.close()
        writer.join(timeout=SETTLE_SECONDS)

        assert waiting
        assert answers == [True]

    def test_a_put_into_a_closed_buffer_is_refused(self) -> None:
        buffer: PrefetchBuffer[str] = PrefetchBuffer(capacity=CAPACITY)
        buffer.close()

        assert not buffer.put(ramp(10), "row")
        assert buffer.queued == 0

    def test_a_buffer_needs_room_for_a_sample(self) -> None:
        with pytest.raises(ValueError):
            PrefetchBuffer(capacity=0)
