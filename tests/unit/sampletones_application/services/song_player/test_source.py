import threading
from typing import Final, List, Optional, Tuple

import numpy as np
import pytest

from sampletones_application.services.song_player.constants import RENDERER_NAME
from sampletones_application.services.song_player.source import SongSource
from sampletones_core.audio.output import AudioThreads, Fill
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.constants.audio import UNITY_GAIN
from tests.suite.audio.ramp import ramp, ramp_indices
from tests.unit.sampletones_application.services.song_player.ramp_song import (
    ROW,
    SYNTHESIS_FAILURE,
    WAIT_SECONDS,
    RampSong,
)

BLOCK: Final[int] = 128
SEEK_ORDER: Final[int] = 2
HALF_GAIN: Final[float] = 0.5
START: Final[SongPosition] = SongPosition(order_position=0, row_index=0)


class MasterGain:
    """The gain a song plays at, which a case moves while the song plays."""

    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class Failures:
    """Every failure a source told between reads."""

    def __init__(self) -> None:
        self.told: List[Exception] = []
        self.arrived = threading.Event()

    def __call__(self, error: Exception) -> None:
        self.told.append(error)
        self.arrived.set()


def _source(
    song: RampSong,
    *,
    looping: bool = False,
    start: SongPosition = START,
    failures: Optional[Failures] = None,
    master_gain: Optional[MasterGain] = None,
) -> SongSource:
    source = SongSource(
        song.factory,
        start=start,
        should_loop=lambda: looping,
        master_gain=MasterGain(UNITY_GAIN) if master_gain is None else master_gain,
        threads=AudioThreads(),
    )
    source.begin(DEFAULT_SAMPLE_RATE, Failures() if failures is None else failures)
    return source


def _read(source: SongSource) -> Tuple[np.ndarray, Fill[SongPosition]]:
    block = np.zeros(BLOCK, dtype=np.float32)
    fill = source.read_into(block)
    return block[: fill.frames], fill


def _read_all(source: SongSource) -> Tuple[np.ndarray, List[SongPosition]]:
    played: List[np.ndarray] = []
    positions: List[SongPosition] = []
    while True:
        samples, fill = _read(source)
        played.append(samples)
        positions.extend(tagged.report for tagged in fill.reports)
        if fill.frames < BLOCK:
            return np.concatenate(played), positions


def _renderers() -> List[threading.Thread]:
    return [thread for thread in threading.enumerate() if thread.name == RENDERER_NAME]


class TestRows:
    """A song plays every row once, in order, each reporting its position once the block holding its end is read."""

    def test_every_row_plays_once_in_order(self) -> None:
        played, positions = _read_all(_source(RampSong([0, 1], rows=4)))

        np.testing.assert_array_equal(ramp_indices(played), np.arange(8 * ROW))
        assert positions == [SongPosition(order_position=order, row_index=row) for order in (0, 1) for row in range(4)]

    def test_the_song_starts_at_the_row_asked_for(self) -> None:
        played, _ = _read_all(_source(RampSong([0, 1], rows=4), start=SongPosition(order_position=1, row_index=2)))

        np.testing.assert_array_equal(ramp_indices(played), np.arange(6 * ROW, 8 * ROW))

    def test_the_synthesizer_renders_at_the_rate_of_the_stream(self) -> None:
        song = RampSong([0], rows=1)

        _read_all(_source(song))

        assert song.rates == [DEFAULT_SAMPLE_RATE]
        assert song.resets == 1

    def test_an_empty_song_ends_at_once(self) -> None:
        played, positions = _read_all(_source(RampSong([], rows=4)))

        assert len(played) == 0
        assert positions == []


class TestMasterGain:
    """Every block plays at the master gain read as it is read, so a change is heard from the next block."""

    def test_the_rows_play_at_the_master_gain(self) -> None:
        played, _ = _read_all(_source(RampSong([0], rows=2), master_gain=MasterGain(HALF_GAIN)))

        np.testing.assert_array_equal(played, ramp(2 * ROW) * HALF_GAIN)

    def test_a_change_is_heard_from_the_next_block(self) -> None:
        master_gain = MasterGain(UNITY_GAIN)
        source = _source(RampSong([0], rows=4), master_gain=master_gain)

        before, _ = _read(source)
        master_gain.value = HALF_GAIN
        after, _ = _read(source)
        source.close()

        np.testing.assert_array_equal(before, ramp(BLOCK))
        np.testing.assert_array_equal(after, ramp(BLOCK, start=BLOCK) * HALF_GAIN)


class TestLooping:
    """A looping song starts over once it reaches its end, and an empty one ends however it loops."""

    def test_a_looping_song_starts_over(self) -> None:
        source = _source(RampSong([0], rows=2), looping=True)

        played = np.concatenate([_read(source)[0] for _ in range(4)])
        source.close()

        assert list(ramp_indices(played[: 4 * ROW])) == [*range(2 * ROW)] * 2

    def test_an_empty_looping_song_ends(self) -> None:
        played, _ = _read_all(_source(RampSong([], rows=2), looping=True))

        assert len(played) == 0


class TestMoves:
    """A seek moves the song to another order at the next row, keeping the voices, and a relocation keeps the row."""

    def test_a_seek_moves_to_the_start_of_the_order(self) -> None:
        song = RampSong([0, 1, 2, 3], rows=4)
        song.held = SongPosition(order_position=0, row_index=1)
        source = _source(song)
        assert song.reached.wait(timeout=WAIT_SECONDS)

        source.seek(SEEK_ORDER)
        song.release.set()
        played, positions = _read_all(source)

        assert positions[:2] == [START, SongPosition(order_position=0, row_index=1)]
        assert positions[2] == SongPosition(order_position=SEEK_ORDER, row_index=0)
        assert song.resets == 1
        np.testing.assert_array_equal(ramp_indices(played[2 * ROW : 3 * ROW]), np.arange(8 * ROW, 9 * ROW))

    def test_a_relocation_keeps_the_row(self) -> None:
        song = RampSong([0, 1, 2, 3], rows=4)
        song.held = SongPosition(order_position=0, row_index=1)
        source = _source(song)
        assert song.reached.wait(timeout=WAIT_SECONDS)

        source.relocate(SEEK_ORDER)
        song.release.set()
        _, positions = _read_all(source)

        assert positions[2] == SongPosition(order_position=SEEK_ORDER, row_index=2)


class TestFailures:
    """A synthesis failure plays every block filled before it, and the read reaching it raises."""

    def test_the_blocks_before_a_failure_play_and_the_next_read_raises(self) -> None:
        source = _source(RampSong([0], rows=4, failing=SongPosition(order_position=0, row_index=3)))
        played = [_read(source)[0] for _ in range(3 * ROW // BLOCK)]

        with pytest.raises(RuntimeError, match=SYNTHESIS_FAILURE):
            _read(source)

        np.testing.assert_array_equal(ramp_indices(np.concatenate(played)), np.arange(len(played) * BLOCK))

    def test_a_song_failing_nowhere_ends_without_raising(self) -> None:
        failures = Failures()

        played, _ = _read_all(_source(RampSong([0], rows=4), failures=failures))

        assert len(played) == 4 * ROW
        assert failures.told == []

    def test_a_failure_is_told_at_once_with_no_read_waiting(self) -> None:
        failures = Failures()

        _source(RampSong([0], rows=4, failing=SongPosition(order_position=0, row_index=0)), failures=failures)

        assert failures.arrived.wait(timeout=WAIT_SECONDS)
        assert [str(error) for error in failures.told] == [SYNTHESIS_FAILURE]


class TestClose:
    """A close wakes a read waiting for a row and ends the render thread, and a source closed first starts none."""

    def test_a_close_wakes_a_read_waiting_for_a_row(self) -> None:
        song = RampSong([0], rows=4)
        song.held = START
        source = _source(song)
        assert song.reached.wait(timeout=WAIT_SECONDS)
        reads: List[int] = []
        reader = threading.Thread(target=lambda: reads.append(_read(source)[1].frames))
        reader.start()

        source.close()
        reader.join(timeout=WAIT_SECONDS)
        song.release.set()

        assert reads == [0]

    def test_a_closed_source_ends_its_render_thread(self) -> None:
        source = _source(RampSong([0] * 100, rows=16))
        _read(source)

        source.close()
        for thread in _renderers():
            thread.join(timeout=WAIT_SECONDS)

        assert _renderers() == []

    def test_a_source_closed_before_it_begins_renders_nothing(self) -> None:
        song = RampSong([0], rows=4)
        source = SongSource(
            song.factory,
            start=START,
            should_loop=lambda: False,
            master_gain=MasterGain(UNITY_GAIN),
            threads=AudioThreads(),
        )

        source.close()
        source.begin(DEFAULT_SAMPLE_RATE, Failures())

        assert song.rates == []
        assert _read(source)[1].frames == 0
