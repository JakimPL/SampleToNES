import threading
from typing import Final, List, Union

import numpy as np
import pytest

from sampletones_core.audio.catalog import DeviceCatalog
from sampletones_core.audio.output import (
    AudioOutput,
    BufferSource,
    EndCause,
    Ending,
    OutputSettings,
    Playback,
    unity_gain,
)
from sampletones_core.constants.audio import DEFAULT_BUFFER_SIZE, DEFAULT_SAMPLE_RATE, BufferSize
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from tests.suite.audio.machine import HEADPHONES, SPEAKERS, FakeAudioSystem, OpenCall, StreamCall
from tests.suite.audio.pacing import StepPacing
from tests.suite.audio.ramp import ramp, ramp_indices
from tests.suite.audio.timeline import Drained, Opened, Terminated
from tests.unit.sampletones_core.audio.output.conftest import HEADPHONES_INDEX
from tests.unit.sampletones_core.audio.output.harness import (
    WAIT_SECONDS,
    AsideFailingSource,
    FailingSource,
    QueuedPost,
    RecordingListener,
    wait_holding,
    wait_until,
)

PREVIEW: Final[int] = 0
NORMAL: Final[int] = 1
SHORT: Final[int] = 4 * DEFAULT_BUFFER_SIZE + 300
LONG: Final[int] = 20 * DEFAULT_SAMPLE_RATE
HEARD: Final[int] = 4 * DEFAULT_BUFFER_SIZE
SEEK_TARGET: Final[int] = 300_000
HALF_GAIN: Final[float] = 0.5
SMALLER_BUFFER: Final[BufferSize] = 256
LENGTH_TOLERANCE: Final[float] = 0.01
QUIET_SECONDS: Final[float] = 0.2
SHORT_DEADLINE: Final[float] = 0.05
GRANTED: Final[int] = 4
WRITER_SECONDS: Final[float] = 10.0
DEVICE_FAILURE: Final[str] = "The device failed"


def _play(
    output: AudioOutput,
    listener: RecordingListener[int],
    *,
    length: int,
    rank: int = NORMAL,
    start: int = 0,
) -> Playback[int]:
    """Plays a ramp of ``length`` samples at the speakers' rate, and asserts the output took it."""
    playback = output.play(
        BufferSource(ramp(length), sample_rate=DEFAULT_SAMPLE_RATE, start=start),
        rank=rank,
        listener=listener,
        gain=unity_gain,
    )
    assert playback is not None
    return playback


def _ended(listener: RecordingListener[int], playback: Playback[int]) -> bool:
    return bool(listener.heard(playback).endings)


def _wait_for_end(post: QueuedPost, listener: RecordingListener[int], playback: Playback[int]) -> None:
    wait_until(lambda: _ended(listener, playback), post, what="the end report")


def _wait_until_written(post: QueuedPost, system: FakeAudioSystem, samples: int) -> None:
    wait_until(lambda: len(system.timeline.written()) >= samples, post, what=f"{samples} samples written")


def _writers() -> List[threading.Thread]:
    return [thread for thread in threading.enumerate() if thread.name.startswith("AudioOutputWriter")]


def _wait_for_quiet(post: QueuedPost, system: FakeAudioSystem) -> None:
    wait_until(lambda: not system.has_open_streams() and not _writers(), post, what="the output to fall quiet")


def _admit(steps: StepPacing, post: QueuedPost, writes: int) -> None:
    """Lets ``writes`` more writes through a stepped device, and waits until the device has taken them."""
    admitted = steps.admitted
    steps.grant(writes)
    wait_until(lambda: steps.admitted == admitted + writes, post, what="the granted writes")


def _causes(listener: RecordingListener[int], playback: Playback[int]) -> List[EndCause]:
    return [ending.cause for ending in listener.heard(playback).endings]


class _Gate:
    """A device call held on its thread until the case opens it, which places a race at that call."""

    def __init__(self) -> None:
        self.arrived = threading.Event()
        self.opened = threading.Event()

    def __call__(self, _call: Union[OpenCall, StreamCall]) -> None:
        if self.opened.is_set():
            return

        self.arrived.set()
        self.opened.wait(timeout=WAIT_SECONDS)


class TestPlayingThrough:
    """Rules 3 and 4: a sound plays every sample once, its positions arrive in order, and it ends once."""

    def test_a_sound_plays_every_sample_once(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        playback = _play(output, listener, length=SHORT)

        _wait_for_end(post, listener, playback)

        np.testing.assert_array_equal(ramp_indices(system.timeline.written()), np.arange(SHORT))
        assert _causes(listener, playback) == [EndCause.FINISHED]

    def test_the_end_lands_once_the_tail_played_out_and_the_stream_closed(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        playback = _play(output, listener, length=SHORT)

        _wait_for_end(post, listener, playback)

        assert listener.heard(playback).streams_open_at_end is False
        assert [event.stream for event in system.timeline.of(Drained)] == list(system.timeline.streams())

    def test_positions_arrive_in_order_before_the_end(
        self,
        output: AudioOutput,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        playback = _play(output, listener, length=SHORT)

        _wait_for_end(post, listener, playback)

        heard = listener.heard(playback)
        assert heard.positions == sorted(heard.positions)
        assert heard.positions[-1] == SHORT
        assert heard.ends_after_positions

    def test_an_output_with_nothing_left_runs_no_thread(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        playback = _play(output, listener, length=SHORT)
        running = bool(_writers())

        _wait_for_end(post, listener, playback)
        _wait_for_quiet(post, system)

        assert running
        assert _writers() == []

    def test_a_sound_plays_at_its_gain(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        playback = output.play(
            BufferSource(ramp(SHORT), sample_rate=DEFAULT_SAMPLE_RATE, start=0),
            rank=NORMAL,
            listener=listener,
            gain=lambda: HALF_GAIN,
        )
        assert playback is not None

        _wait_for_end(post, listener, playback)

        np.testing.assert_allclose(system.timeline.written(), ramp(SHORT) * HALF_GAIN)


class TestClaims:
    """Rules 1 and 2: a claim below the holder is declined, any other takes the output on a stream of its own."""

    def test_a_claim_below_the_holder_is_declined(
        self,
        realtime_output: AudioOutput,
        realtime_listener: RecordingListener[int],
    ) -> None:
        holder = _play(realtime_output, realtime_listener, length=LONG)

        declined = realtime_output.play(
            BufferSource(ramp(SHORT), sample_rate=DEFAULT_SAMPLE_RATE, start=0),
            rank=PREVIEW,
            listener=realtime_listener,
            gain=unity_gain,
        )

        assert declined is None
        assert holder.engaged

    def test_a_claim_at_the_holder_rank_takes_the_output(
        self,
        realtime_output: AudioOutput,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        taken = _play(realtime_output, realtime_listener, length=LONG, rank=PREVIEW)

        taker = _play(realtime_output, realtime_listener, length=LONG, rank=PREVIEW)
        _wait_for_end(post, realtime_listener, taken)

        assert taker.engaged
        assert _causes(realtime_listener, taken) == [EndCause.TAKEN]

    def test_a_takeover_cuts_the_stream_and_opens_one_of_its_own(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        taken = _play(realtime_output, realtime_listener, length=LONG)
        _wait_until_written(post, realtime_system, HEARD)

        _play(realtime_output, realtime_listener, length=LONG)
        wait_until(lambda: len(realtime_system.timeline.streams()) == 2, post, what="the taker's stream")
        realtime_output.stop_all()
        _wait_for_quiet(post, realtime_system)

        assert _causes(realtime_listener, taken) == [EndCause.TAKEN]
        assert realtime_system.timeline.most_streams_open() == 1
        assert not realtime_system.timeline.of(Drained)

    def test_no_device_in_force_refuses_a_sound_before_a_thread_starts(
        self,
        output: AudioOutput,
        listener: RecordingListener[int],
    ) -> None:
        output.configure(OutputSettings(device=None, buffer_size=DEFAULT_BUFFER_SIZE))

        with pytest.raises(NoOutputDeviceError):
            _play(output, listener, length=SHORT)

        assert not output.is_sounding


class TestStop:
    """Rule 6: a stop silences the sound at once and cuts its tail, and the caller waits on no device."""

    def test_a_stopped_sound_ends_once_and_is_cut(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        playback = _play(realtime_output, realtime_listener, length=LONG)
        _wait_until_written(post, realtime_system, HEARD)

        assert playback.stop()
        _wait_for_quiet(post, realtime_system)

        assert _causes(realtime_listener, playback) == [EndCause.STOPPED]
        assert not realtime_system.timeline.of(Drained)

    def test_a_stop_returns_while_the_writer_is_held_inside_a_write(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        gate = _Gate()
        system.hooks.before_write = gate
        playback = _play(output, listener, length=LONG)
        assert gate.arrived.wait(timeout=WAIT_SECONDS)

        output.stop_all()
        held = not gate.opened.is_set()
        gate.opened.set()
        _wait_for_end(post, listener, playback)

        assert held
        assert not playback.engaged
        assert _causes(listener, playback) == [EndCause.STOPPED]

    def test_a_stop_while_the_stream_opens_sounds_nothing(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        gate = _Gate()
        system.hooks.before_open = gate
        playback = _play(output, listener, length=SHORT)
        assert gate.arrived.wait(timeout=WAIT_SECONDS)

        playback.stop()
        gate.opened.set()
        _wait_for_quiet(post, system)

        assert len(system.timeline.written()) == 0
        assert _causes(listener, playback) == [EndCause.STOPPED]


class TestPause:
    """A paused sound holds the stream open and the device takes nothing, until it resumes from where it stood."""

    def test_a_paused_sound_writes_nothing_and_resumes_where_it_stood(
        self,
        stepped_output: AudioOutput,
        stepped_system: FakeAudioSystem,
        steps: StepPacing,
        post: QueuedPost,
        stepped_listener: RecordingListener[int],
    ) -> None:
        playback = _play(stepped_output, stepped_listener, length=LONG)
        assert steps.wait_for_writer(timeout=WRITER_SECONDS)
        _admit(steps, post, GRANTED)
        assert steps.wait_for_writer(timeout=WRITER_SECONDS)
        playback.pause()
        _admit(steps, post, 1)

        writing_while_paused = steps.wait_for_writer(timeout=QUIET_SECONDS)
        playback.resume()
        resumed = steps.wait_for_writer(timeout=WRITER_SECONDS)
        steps.grant(GRANTED)
        _wait_until_written(post, stepped_system, (2 * GRANTED + 1) * DEFAULT_BUFFER_SIZE)

        assert not writing_while_paused
        assert resumed
        assert stepped_system.has_open_streams()
        written = ramp_indices(stepped_system.timeline.written())
        np.testing.assert_array_equal(written, np.arange(len(written)))


class TestCommands:
    """Rule 4: a command reaches a sound before its next read, a mark after a seek reads the seek, and a sound
    whose end is decided refuses it."""

    def test_a_seek_plays_on_from_the_target(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        source = BufferSource(ramp(LONG), sample_rate=DEFAULT_SAMPLE_RATE, start=0)
        playback = realtime_output.play(source, rank=NORMAL, listener=realtime_listener, gain=unity_gain)
        assert playback is not None
        _wait_until_written(post, realtime_system, HEARD)
        heard = len(realtime_listener.heard(playback).positions)

        assert playback.command(lambda: source.seek(SEEK_TARGET))
        _wait_until_written(post, realtime_system, len(realtime_system.timeline.written()) + HEARD)
        playback.stop()
        _wait_for_quiet(post, realtime_system)

        written = ramp_indices(realtime_system.timeline.written())
        jump = int(np.flatnonzero(written == SEEK_TARGET)[0])
        np.testing.assert_array_equal(written[jump:], np.arange(SEEK_TARGET, SEEK_TARGET + len(written) - jump))
        after = realtime_listener.heard(playback).positions[heard:]
        assert after
        assert all(position > SEEK_TARGET for position in after)

    def test_a_position_read_before_a_seek_lands_dropped(
        self,
        stepped_output: AudioOutput,
        stepped_system: FakeAudioSystem,
        steps: StepPacing,
        post: QueuedPost,
        stepped_listener: RecordingListener[int],
    ) -> None:
        source = BufferSource(ramp(LONG), sample_rate=DEFAULT_SAMPLE_RATE, start=0)
        playback = stepped_output.play(source, rank=NORMAL, listener=stepped_listener, gain=unity_gain)
        assert playback is not None
        assert steps.wait_for_writer(timeout=WRITER_SECONDS)
        steps.grant(1)
        wait_holding(lambda: post.waiting > 0, what="the first block's position")
        waiting = post.waiting

        playback.command(lambda: source.seek(SEEK_TARGET))
        post.drain()
        before_the_seek_played = list(stepped_listener.heard(playback).positions)
        steps.grant(2)
        wait_until(lambda: bool(stepped_listener.heard(playback).positions), post, what="a position after the seek")

        assert waiting
        assert before_the_seek_played == []
        assert all(position > SEEK_TARGET for position in stepped_listener.heard(playback).positions)

    def test_a_command_to_a_sound_that_ended_is_refused(
        self,
        output: AudioOutput,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        playback = _play(output, listener, length=SHORT)
        _wait_for_end(post, listener, playback)
        ran: List[bool] = []

        accepted = playback.command(lambda: ran.append(True))

        assert not accepted
        assert ran == []

    def test_a_command_to_a_playing_sound_runs_on_the_writer(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        playback = _play(realtime_output, realtime_listener, length=LONG)
        threads: List[str] = []

        assert playback.command(lambda: threads.append(threading.current_thread().name))
        _wait_until_written(post, realtime_system, HEARD)

        assert threads and threads[0].startswith("AudioOutputWriter")


class TestFailures:
    """Rule 7: a failure ends the sound once, naming the failure, and the next sound plays."""

    def test_a_refused_stream_fails_the_sound_and_the_next_one_plays(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        system.occupy()
        refused = _play(output, listener, length=SHORT)
        _wait_for_end(post, listener, refused)
        system.free()

        played = _play(output, listener, length=SHORT)
        _wait_for_end(post, listener, played)

        endings = listener.heard(refused).endings
        assert [ending.cause for ending in endings] == [EndCause.FAILED]
        assert isinstance(endings[0].error, PlaybackError)
        assert _causes(listener, played) == [EndCause.FINISHED]

    def test_a_failed_write_fails_the_sound_once(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        def fail(_call: StreamCall) -> None:
            raise OSError(DEVICE_FAILURE)

        system.hooks.before_write = fail
        playback = _play(output, listener, length=SHORT)

        _wait_for_end(post, listener, playback)
        _wait_for_quiet(post, system)

        assert _causes(listener, playback) == [EndCause.FAILED]
        assert not system.timeline.violations()

    def test_a_failed_drain_fails_the_finished_sound(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        def fail(_call: StreamCall) -> None:
            raise OSError(DEVICE_FAILURE)

        system.hooks.before_drain = fail
        playback = _play(output, listener, length=SHORT)

        _wait_for_end(post, listener, playback)

        assert _causes(listener, playback) == [EndCause.FAILED]
        assert not system.has_open_streams()

    def test_a_failing_source_fails_its_sound_and_the_next_one_plays(
        self,
        output: AudioOutput,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        source = FailingSource(failing_read=2)
        failing = output.play(source, rank=NORMAL, listener=listener, gain=unity_gain)
        assert failing is not None
        _wait_for_end(post, listener, failing)

        played = _play(output, listener, length=SHORT)
        _wait_for_end(post, listener, played)

        assert listener.heard(failing).endings == [Ending.failure(source.error)]
        assert _causes(listener, played) == [EndCause.FINISHED]


class TestFailuresAside:
    """Rule 7: a source failing on a thread of its own ends its playback at once, sounding or held paused."""

    def test_a_source_failing_while_paused_ends_its_playback_once(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        source = AsideFailingSource()
        playback = realtime_output.play(source, rank=NORMAL, listener=realtime_listener, gain=unity_gain)
        assert playback is not None
        _wait_until_written(post, realtime_system, HEARD)
        playback.pause()

        source.fail()
        _wait_for_end(post, realtime_listener, playback)
        _wait_for_quiet(post, realtime_system)

        assert realtime_listener.heard(playback).endings == [Ending.failure(source.error)]

    def test_a_source_failing_after_its_stop_tells_nothing_more(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        source = AsideFailingSource()
        playback = realtime_output.play(source, rank=NORMAL, listener=realtime_listener, gain=unity_gain)
        assert playback is not None
        _wait_until_written(post, realtime_system, HEARD)
        playback.stop()

        source.fail()
        _wait_for_quiet(post, realtime_system)

        assert _causes(realtime_listener, playback) == [EndCause.STOPPED]


class TestRates:
    """Rule 5: a sound plays at its own pitch and length on a device of any rate."""

    def test_a_sound_keeps_its_length_on_a_faster_device(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        output.configure(_headphones(output))

        playback = _play(output, listener, length=SHORT)
        _wait_for_end(post, listener, playback)

        expected = SHORT * HEADPHONES.default_sample_rate / DEFAULT_SAMPLE_RATE
        assert len(system.timeline.written()) == pytest.approx(expected, rel=LENGTH_TOLERANCE)
        assert system.timeline.of(Opened)[0].sample_rate == HEADPHONES.default_sample_rate


class TestConfigure:
    """A device change ends every sound and the next opens on the new device, and a buffer size waits for it."""

    def test_a_device_change_stops_the_sound_and_the_next_plays_on_the_new_device(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        playing = _play(realtime_output, realtime_listener, length=LONG)
        _wait_until_written(post, realtime_system, HEARD)

        realtime_output.configure(_headphones(realtime_output))
        _wait_for_end(post, realtime_listener, playing)
        _play(realtime_output, realtime_listener, length=LONG)
        wait_until(lambda: len(realtime_system.timeline.streams()) == 2, post, what="a stream on the headphones")

        assert _causes(realtime_listener, playing) == [EndCause.STOPPED]
        assert realtime_system.timeline.of(Opened)[-1].device == HEADPHONES_INDEX
        assert realtime_system.timeline.most_streams_open() == 1

    def test_a_buffer_size_change_leaves_the_sound_playing(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        playing = _play(realtime_output, realtime_listener, length=LONG)
        _wait_until_written(post, realtime_system, HEARD)

        realtime_output.configure(
            OutputSettings(device=realtime_output.catalog.default_device(), buffer_size=SMALLER_BUFFER)
        )
        _wait_until_written(post, realtime_system, 2 * HEARD)

        assert playing.engaged
        assert len(realtime_system.timeline.streams()) == 1


class TestRefresh:
    """A refresh renews the backend while no stream is open, finds the device again, and tells what it lists."""

    def test_a_refresh_renews_the_backend_and_reports_the_devices(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
    ) -> None:
        catalogs: List[DeviceCatalog] = []
        system.devices = [HEADPHONES, SPEAKERS]

        output.refresh(catalogs.append)
        wait_until(lambda: bool(catalogs), post, what="the refreshed devices")

        assert len(system.drivers) == 2
        assert system.drivers[0].terminated
        assert [device.name for device in catalogs[0].devices.values()] == [HEADPHONES.name, SPEAKERS.name]

    def test_a_refreshed_backend_plays_on_the_device_found_by_its_name(
        self,
        output: AudioOutput,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        catalogs: List[DeviceCatalog] = []
        system.devices = [HEADPHONES, SPEAKERS]
        output.refresh(catalogs.append)
        wait_until(lambda: bool(catalogs), post, what="the refreshed devices")

        playback = _play(output, listener, length=SHORT)
        _wait_for_end(post, listener, playback)

        assert system.timeline.of(Opened)[-1].device == catalogs[0].find(SPEAKERS.name)

    def test_a_refresh_stops_the_sound_playing(
        self,
        realtime_output: AudioOutput,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        playing = _play(realtime_output, realtime_listener, length=LONG)
        _wait_until_written(post, realtime_system, HEARD)

        realtime_output.refresh(lambda _catalog: None)
        _wait_for_end(post, realtime_listener, playing)
        _wait_for_quiet(post, realtime_system)

        assert _causes(realtime_listener, playing) == [EndCause.STOPPED]
        assert not realtime_system.timeline.violations()


class TestClose:
    """Rule 8: after the teardown every audio thread has ended and every stream is closed, and a writer that
    outlives the deadline keeps the backend alive."""

    def test_closing_ends_every_sound_and_terminates_the_backend(
        self,
        realtime_system: FakeAudioSystem,
        post: QueuedPost,
        realtime_listener: RecordingListener[int],
    ) -> None:
        output = AudioOutput(realtime_system.driver, post=post)
        output.configure(OutputSettings(device=output.catalog.default_device(), buffer_size=DEFAULT_BUFFER_SIZE))
        playback = _play(output, realtime_listener, length=LONG)
        _wait_until_written(post, realtime_system, HEARD)

        output.close(deadline_seconds=WAIT_SECONDS)
        post.drain()

        assert _causes(realtime_listener, playback) == [EndCause.STOPPED]
        assert _writers() == []
        assert not realtime_system.has_open_streams()
        assert realtime_system.timeline.of(Terminated)

    def test_a_writer_outliving_the_deadline_keeps_the_backend(
        self,
        system: FakeAudioSystem,
        post: QueuedPost,
        listener: RecordingListener[int],
    ) -> None:
        gate = _Gate()
        system.hooks.before_open = gate
        output = AudioOutput(system.driver, post=post)
        output.configure(OutputSettings(device=output.catalog.default_device(), buffer_size=DEFAULT_BUFFER_SIZE))
        playback = _play(output, listener, length=SHORT)
        assert gate.arrived.wait(timeout=WAIT_SECONDS)

        output.close(deadline_seconds=SHORT_DEADLINE)
        post.drain()
        terminated = bool(system.timeline.of(Terminated))
        gate.opened.set()
        _wait_for_quiet(post, system)

        assert not terminated
        assert _causes(listener, playback) == [EndCause.STOPPED]
        assert not system.timeline.violations()

    def test_a_claim_after_the_close_is_declined(
        self,
        output: AudioOutput,
        listener: RecordingListener[int],
    ) -> None:
        output.close(deadline_seconds=WAIT_SECONDS)

        declined = output.play(
            BufferSource(ramp(SHORT), sample_rate=DEFAULT_SAMPLE_RATE, start=0),
            rank=NORMAL,
            listener=listener,
            gain=unity_gain,
        )

        assert declined is None


def _headphones(output: AudioOutput) -> OutputSettings:
    return OutputSettings(
        device=output.catalog.configured(HEADPHONES_INDEX, HEADPHONES.default_sample_rate),
        buffer_size=DEFAULT_BUFFER_SIZE,
    )
