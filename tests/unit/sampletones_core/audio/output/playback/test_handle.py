from typing import Final

import numpy as np
import pytest

from sampletones_core.audio.output import BufferSource, EndCause, Ending, Playback, unity_gain
from sampletones_core.audio.output.playback import PlaybackFeed
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_shared.types.callback import VoidCallback
from tests.suite.audio.ramp import ramp
from tests.unit.sampletones_core.audio.output.harness import QueuedPost, RecordingListener

LENGTH: Final[int] = 4096
BLOCK: Final[int] = 256
SEEK_TARGET: Final[int] = 2048
FINISHED: Final[Ending] = Ending.of(EndCause.FINISHED)


class _Output:
    """An output deciding nothing, so a case drives the playback's own side alone: every command is taken."""

    def is_engaged(self, _feed: PlaybackFeed) -> bool:
        return True

    def is_paused(self, _feed: PlaybackFeed) -> bool:
        return False

    def pause(self, _feed: PlaybackFeed) -> bool:
        return True

    def resume(self, _feed: PlaybackFeed) -> bool:
        return True

    def stop(self, _feed: PlaybackFeed) -> bool:
        return True

    def command(self, feed: PlaybackFeed, action: VoidCallback) -> bool:
        feed.enqueue(action)
        return True

    def fail(self, _feed: PlaybackFeed, _error: Exception) -> bool:
        return True


def _now(delivery: VoidCallback) -> None:
    delivery()


@pytest.fixture
def listener() -> RecordingListener[int]:
    return RecordingListener(streams_open=lambda: False)


@pytest.fixture
def source() -> BufferSource:
    return BufferSource(ramp(LENGTH), sample_rate=DEFAULT_SAMPLE_RATE, start=0)


def _playback(source: BufferSource, listener: RecordingListener[int], post: QueuedPost) -> Playback[int]:
    return Playback(source, gain=unity_gain, listener=listener, post=post, control=_Output())


def _block(playback: Playback[int]) -> None:
    """One step of the writer: the commands taken, the block read, and its positions handed on."""
    playback.take_commands()
    playback.read_into(np.zeros(BLOCK, dtype=np.float32), output_rate=DEFAULT_SAMPLE_RATE)
    playback.heard()


class TestPositions:
    """Rule 4: positions land in order, a position read before a later command is dropped, and none after the end."""

    def test_every_block_lands_its_position_in_order(
        self,
        source: BufferSource,
        listener: RecordingListener[int],
    ) -> None:
        post = QueuedPost()
        playback = _playback(source, listener, post)

        _block(playback)
        _block(playback)
        post.drain()

        assert listener.heard(playback).positions == [BLOCK, 2 * BLOCK]

    def test_a_position_read_before_a_command_is_dropped(
        self,
        source: BufferSource,
        listener: RecordingListener[int],
    ) -> None:
        post = QueuedPost()
        playback = _playback(source, listener, post)
        _block(playback)

        playback.command(lambda: source.seek(SEEK_TARGET))
        post.drain()
        dropped = list(listener.heard(playback).positions)
        _block(playback)
        post.drain()

        assert dropped == []
        assert listener.heard(playback).positions == [SEEK_TARGET + BLOCK]

    def test_a_position_landing_after_the_end_is_dropped(
        self,
        source: BufferSource,
        listener: RecordingListener[int],
    ) -> None:
        post = QueuedPost()
        playback = _playback(source, listener, post)
        playback.take_commands()
        playback.read_into(np.zeros(BLOCK, dtype=np.float32), output_rate=DEFAULT_SAMPLE_RATE)

        playback.end(FINISHED)
        playback.heard()
        post.drain()

        assert listener.heard(playback).positions == []
        assert listener.heard(playback).endings == [FINISHED]


class TestEnd:
    """Rule 3: a playback sends one end report, however often it is told its end."""

    def test_a_second_end_sends_nothing(self, source: BufferSource, listener: RecordingListener[int]) -> None:
        post = QueuedPost()
        playback = _playback(source, listener, post)

        playback.end(FINISHED)
        playback.end(Ending.of(EndCause.STOPPED))
        post.drain()

        assert listener.heard(playback).endings == [FINISHED]

    def test_a_post_delivering_at_once_lands_every_report(
        self,
        source: BufferSource,
        listener: RecordingListener[int],
    ) -> None:
        playback = Playback(source, gain=unity_gain, listener=listener, post=_now, control=_Output())

        _block(playback)
        playback.end(FINISHED)

        heard = listener.heard(playback)
        assert heard.positions == [BLOCK]
        assert heard.endings == [FINISHED]


class TestBegin:
    """A playback begins its source once, at its first read, at the rate of the stream."""

    def test_the_source_begins_at_the_rate_of_the_stream(self, listener: RecordingListener[int]) -> None:
        source = BufferSource(ramp(LENGTH), sample_rate=2 * DEFAULT_SAMPLE_RATE, start=0)
        playback = _playback(source, listener, QueuedPost())

        frames = playback.read_into(np.zeros(BLOCK, dtype=np.float32), output_rate=DEFAULT_SAMPLE_RATE)
        playback.read_into(np.zeros(BLOCK, dtype=np.float32), output_rate=DEFAULT_SAMPLE_RATE)

        assert frames == BLOCK
        assert source.position == 4 * BLOCK
