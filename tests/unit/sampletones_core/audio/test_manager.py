import threading
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import Any, Callable, Dict, Final, Iterator, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_core.audio.device import CurrentDevice
from sampletones_core.audio.lease import OutputLease
from sampletones_core.audio.manager import AudioDeviceManager
from sampletones_core.audio.stream import write_to_stream
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO, SampleRate
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from tests.suite.audio.machine import (
    SPEAKERS,
    FakeAudioDriver,
    FakeAudioSystem,
    OpenCall,
    StreamCall,
    ticking_machine,
)
from tests.suite.audio.timeline import Closed, Drained, Opened, Terminated
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

_LOW = 0
_HIGH = 1
_RELEASE_TIMEOUT: Final[float] = 5.0
_OPEN_DELAY: Final[float] = 0.2
_SHORT_JOIN: Final[float] = 0.05
_STOP_JOIN_TARGET: Final[str] = "sampletones_core.audio.manager.STOP_JOIN_SECONDS"
_LET_GO_JOIN_TARGET: Final[str] = "sampletones_core.audio.manager.LET_GO_JOIN_SECONDS"
_SPEAKERS_INDEX: Final[int] = 0
_CHOSEN_RATE: Final[SampleRate] = 48000
_AUDIO_FILE: Final[str] = "recording.wav"
_LOAD_AUDIO: Final[str] = "sampletones_core.audio.manager.load_audio"


def _manager() -> AudioDeviceManager:
    """A manager on a fake machine whose speakers are its default output, playing faster than real time."""
    return AudioDeviceManager(ticking_machine([SPEAKERS], default_device=_SPEAKERS_INDEX).driver)


def _system(manager: AudioDeviceManager) -> FakeAudioSystem:
    """The fake machine ``manager`` reaches its backend on."""
    driver = manager._driver
    assert isinstance(driver, FakeAudioDriver)
    return driver.system


def _refusing(manager: AudioDeviceManager, reason: str) -> None:
    """Makes the device refuse every stream ``manager`` opens, naming ``reason``."""

    def refuse(_call: OpenCall) -> None:
        raise OSError(reason)

    _system(manager).hooks.before_open = refuse


def _failing(reason: str) -> Callable[[StreamCall], None]:
    """A hook failing the call it runs before, as a device that went away does."""

    def fail(_call: StreamCall) -> None:
        raise OSError(reason)

    return fail


def _closed_unplayed(system: FakeAudioSystem) -> bool:
    """Whether the one stream the device opened closed without playing a sample."""
    [opened] = system.timeline.of(Opened)
    return [closed.stream for closed in system.timeline.of(Closed)] == [opened.stream] and system.timeline.written(
        opened.stream
    ).size == 0


class _Holder:
    """A source streaming under a lease, which hands it back from the thread that was writing to it.

    Mirrors the song player: the release runs on the caller's thread while the hand-back comes from
    the writer, so the two meet only while the manager holds no lock across a release. The writer is
    built from the ``Thread`` this module imported, which cases patching the manager's thread factory
    leave in place.
    """

    def __init__(self, manager: AudioDeviceManager) -> None:
        self._manager = manager
        self.lease: Optional[OutputLease] = None
        self.releases: int = 0
        self.handed_back = threading.Event()

    def claim(self, priority: int) -> Optional[OutputLease]:
        self.lease = self._manager.acquire_output(priority=priority, release=self.release)
        return self.lease

    def release(self) -> None:
        self.releases += 1
        writer = Thread(target=self._hand_back, daemon=True)
        writer.start()
        writer.join(timeout=_RELEASE_TIMEOUT)

    def _hand_back(self) -> None:
        if self.lease is not None:
            self._manager.hand_back(self.lease)

        self.handed_back.set()


def _streaming_holder(manager: AudioDeviceManager, priority: int) -> _Holder:
    """A holder whose claim was granted and whose stream is open."""
    holder = _Holder(manager)
    lease = holder.claim(priority)
    assert lease is not None
    assert manager.open_output_stream(lease, sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800) is not None
    return holder


def _holding_manager(release: Callable[[], None]) -> AudioDeviceManager:
    """A manager with one stream open under a lease whose holder answers ``release``."""
    manager = _manager()
    manager.stop = MagicMock()
    lease = OutputLease(priority=_LOW, release=release, stream=MagicMock())
    manager._claims = [lease]
    manager._outstanding = [lease]
    return manager


class TestSingleOutputExclusion:
    """The output device allows one open stream, so the two playback paths must release each other."""

    def test_a_claim_stops_internal_playback(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()

        lease = manager.acquire_output(priority=_LOW, release=MagicMock())

        manager.stop.assert_called_once()
        assert lease is not None

    def test_play_releases_a_lease_it_outranks(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        holder = _streaming_holder(manager, _LOW)

        with patch("sampletones_core.audio.manager.threading.Thread"):
            took = manager.play(np.zeros(4, dtype=np.float32), priority=_HIGH)

        assert took is True
        assert holder.handed_back.is_set()
        assert manager._outstanding == []


class TestPriorityArbitration:
    """A lower-priority request yields to active higher-priority playback; ties take over."""

    def test_yields_to_a_higher_lease(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        holder = _streaming_holder(manager, _HIGH)
        manager.stop.reset_mock()

        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            took = manager.play(np.zeros(4, dtype=np.float32), priority=_LOW)

        assert took is False
        thread.assert_not_called()
        manager.stop.assert_not_called()
        assert holder.releases == 0

    def test_yields_to_higher_internal_priority(self) -> None:
        manager = _manager()
        manager._playing = True
        manager._active_priority = _HIGH
        manager.stop = MagicMock()

        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(4, dtype=np.float32), priority=_LOW)

        thread.assert_not_called()

    def test_equal_priority_takes_over(self) -> None:
        manager = _manager()
        manager._playing = True
        manager._active_priority = _LOW
        manager.stop = MagicMock()

        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(4, dtype=np.float32), priority=_LOW)

        thread.assert_called_once()

    def test_higher_priority_takes_over(self) -> None:
        manager = _manager()
        manager._playing = True
        manager._active_priority = _LOW
        manager.stop = MagicMock()

        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(4, dtype=np.float32), priority=_HIGH)

        thread.assert_called_once()


class TestPlaybackStart(BaseTestSuite):
    """Playback begins at the sample asked for, placed before the thread writing it starts."""

    AUDIO_LENGTH: Final[int] = 8

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        start: int
        expected: int

    test_cases = (
        TestCase(start=5, expected=5, label="within_the_audio"),
        TestCase(start=-3, expected=0, label="before_the_audio_clamps_to_its_beginning"),
        TestCase(start=AUDIO_LENGTH + 4, expected=AUDIO_LENGTH, label="past_the_audio_clamps_to_its_end"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_playback_begins_at_the_start_asked_for(self, test_case: TestCase) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        positions_at_thread_start: List[int] = []

        def thread(**_kwargs: object) -> MagicMock:
            started = MagicMock()
            started.start.side_effect = lambda: positions_at_thread_start.append(manager._position)
            return started

        with patch("sampletones_core.audio.manager.threading.Thread", side_effect=thread):
            manager.play(np.zeros(self.AUDIO_LENGTH, dtype=np.float32), start=test_case.start)

        assert positions_at_thread_start == [test_case.expected]


class TestAStreamTheDeviceRefuses:
    """A stream the device refuses to open leaves the playback idle before the refusal is reported."""

    def test_the_playback_reads_stopped_when_the_refusal_is_reported(self) -> None:
        manager = _manager()
        _refusing(manager, "the device is busy")
        manager._position_callback = MagicMock()
        playing_when_reported: List[bool] = []
        manager.on_playback_error = lambda _error: playing_when_reported.append(manager.is_playing())
        manager._playing = True
        manager._audio_data = np.zeros(TestPlaybackStart.AUDIO_LENGTH, dtype=np.float32)

        manager._playback_worker(output=manager.require_output(), update=True, generation=manager._generation)

        assert playing_when_reported == [False]
        manager._position_callback.assert_called_once_with(0)

    def test_a_stream_refused_under_a_lease_raises_a_playback_error(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        _refusing(manager, "the device is busy")
        lease = manager.acquire_output(priority=_LOW, release=MagicMock())
        assert lease is not None

        with pytest.raises(PlaybackError, match="the device is busy"):
            manager.open_output_stream(lease, sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800)

        assert manager._outstanding == []

    def test_both_kinds_of_playback_name_the_refusal_alike(self) -> None:
        """A refused stream reads the same whether the manager plays the audio or hands the stream out."""
        manager = _manager()
        manager.stop = MagicMock()
        _refusing(manager, "the device is busy")
        manager._position_callback = None
        reported: List[Exception] = []
        manager.on_playback_error = reported.append
        manager._playing = True
        manager._audio_data = np.zeros(TestPlaybackStart.AUDIO_LENGTH, dtype=np.float32)
        manager._playback_worker(output=manager.require_output(), update=False, generation=manager._generation)
        lease = manager.acquire_output(priority=_LOW, release=MagicMock())
        assert lease is not None

        with pytest.raises(PlaybackError) as raised:
            manager.open_output_stream(lease, sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800)

        assert [str(error) for error in reported] == [str(raised.value)]


class TestAPlaybackANewerOneReplaced:
    """A worker whose stream opens only after a newer play leaves the newer playback as it stands.

    Stopping waits a while for the worker, and a device slow to open can keep it longer, so the older
    worker can come back after the newer play has begun. Its refusal is the older playback's alone, and a
    stream it opened late closes without a sound.
    """

    FIRST_LENGTH: Final[int] = 8
    SECOND_LENGTH: Final[int] = 16

    @pytest.fixture(name="replaced")
    def replaced_fixture(self) -> Tuple[AudioDeviceManager, Dict[str, Any]]:
        """A manager playing a second buffer, and the arguments the worker of the first one was started with."""
        manager = _manager()
        manager._buffer_size = self.FIRST_LENGTH
        manager._position_callback = MagicMock()
        manager._playback_thread = None
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(self.FIRST_LENGTH, dtype=np.float32))
            manager.play(np.ones(self.SECOND_LENGTH, dtype=np.float32))

        manager._position_callback.reset_mock()
        return manager, thread.call_args_list[0].kwargs["kwargs"]

    @staticmethod
    def assert_the_newer_playback_stands(manager: AudioDeviceManager) -> None:
        assert manager.is_playing()
        assert manager._audio_data is not None
        assert len(manager._audio_data) == TestAPlaybackANewerOneReplaced.SECOND_LENGTH
        manager._position_callback.assert_not_called()

    def test_an_older_worker_refused_late_leaves_the_newer_playback_alone(
        self,
        replaced: Tuple[AudioDeviceManager, Dict[str, Any]],
    ) -> None:
        manager, first_worker = replaced
        _refusing(manager, "the device is busy")
        reported: List[Exception] = []
        manager.on_playback_error = reported.append

        manager._playback_worker(**first_worker)

        self.assert_the_newer_playback_stands(manager)
        assert reported == []

    def test_an_older_worker_opened_late_closes_its_stream_unplayed(
        self,
        replaced: Tuple[AudioDeviceManager, Dict[str, Any]],
    ) -> None:
        manager, first_worker = replaced

        manager._playback_worker(**first_worker)

        assert _closed_unplayed(_system(manager))
        self.assert_the_newer_playback_stands(manager)

    def test_the_newer_worker_refused_reports_it(
        self,
        replaced: Tuple[AudioDeviceManager, Dict[str, Any]],
    ) -> None:
        """The refusal of the playback in force still reaches the reader."""
        manager, _ = replaced
        _refusing(manager, "the device is busy")
        reported: List[Exception] = []
        manager.on_playback_error = reported.append
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.ones(self.SECOND_LENGTH, dtype=np.float32))

        manager._playback_worker(**thread.call_args.kwargs["kwargs"])

        assert len(reported) == 1
        assert not manager.is_playing()


class TestADeviceFailingMidPlayback:
    """A write or a stop the device fails leaves the playback idle, and then reports the failure once.

    The failure reaches the reader the way a refused stream does, and only while the playback that met it
    is the one in force.
    """

    LENGTH: Final[int] = 8

    @pytest.fixture(name="playing")
    def playing_fixture(self) -> Tuple[AudioDeviceManager, Dict[str, Any], FakeAudioSystem]:
        """A manager playing a buffer, the arguments its worker was started with, and the machine it plays on."""
        manager = _manager()
        manager._buffer_size = self.LENGTH
        manager._position_callback = None
        manager._playback_thread = None
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(self.LENGTH, dtype=np.float32))

        return manager, thread.call_args.kwargs["kwargs"], _system(manager)

    @staticmethod
    def record_reports(manager: AudioDeviceManager) -> List[Tuple[PlaybackError, bool]]:
        """Notes each failure reported with whether the playback read playing then."""
        reports: List[Tuple[PlaybackError, bool]] = []
        manager.on_playback_error = lambda error: reports.append((error, manager.is_playing()))
        return reports

    def test_a_failed_write_is_reported_once_with_the_playback_stopped(
        self,
        playing: Tuple[AudioDeviceManager, Dict[str, Any], FakeAudioSystem],
    ) -> None:
        manager, worker, system = playing
        system.hooks.before_write = _failing("the device went away")
        reports = self.record_reports(manager)

        manager._playback_worker(**worker)

        assert [is_playing for _, is_playing in reports] == [False]
        assert "the device went away" in str(reports[0][0])
        assert len(system.timeline.of(Closed)) == 1

    def test_a_failed_stop_still_closes_the_stream_and_leaves_the_playback_idle(
        self,
        playing: Tuple[AudioDeviceManager, Dict[str, Any], FakeAudioSystem],
    ) -> None:
        manager, worker, system = playing
        system.hooks.before_drain = _failing("the device went away")
        reports = self.record_reports(manager)

        manager._playback_worker(**worker)

        assert [is_playing for _, is_playing in reports] == [False]
        assert len(system.timeline.of(Closed)) == 1
        assert not manager.is_playing()

    def test_a_write_failing_after_a_newer_play_reports_nothing(
        self,
        playing: Tuple[AudioDeviceManager, Dict[str, Any], FakeAudioSystem],
    ) -> None:
        """The newer playback stands, and the failure belongs to the playback it replaced."""
        manager, worker, system = playing

        def replaced_then_failing(_call: StreamCall) -> None:
            with patch("sampletones_core.audio.manager.threading.Thread"):
                manager.play(np.ones(self.LENGTH, dtype=np.float32))
            raise OSError("the device went away")

        system.hooks.before_write = replaced_then_failing
        reports = self.record_reports(manager)

        manager._playback_worker(**worker)

        assert reports == []
        assert manager.is_playing()

    def test_a_failed_write_reads_as_the_failed_write_of_a_handed_out_stream(
        self,
        playing: Tuple[AudioDeviceManager, Dict[str, Any], FakeAudioSystem],
    ) -> None:
        """Both kinds of playback name the failure alike, so the reader reads the same words."""
        manager, worker, system = playing
        system.hooks.before_write = _failing("the device went away")
        reports = self.record_reports(manager)
        manager._playback_worker(**worker)
        stream = system.driver().open_output(
            device_index=_SPEAKERS_INDEX, sample_rate=DEFAULT_SAMPLE_RATE, frames_per_buffer=None
        )

        with pytest.raises(PlaybackError) as raised:
            write_to_stream(stream, np.zeros(self.LENGTH, dtype=np.float32).tobytes())

        assert [str(error) for error, _ in reports] == [str(raised.value)]


class TestAPlaybackAStopLetGo:
    """A worker a stop let go of plays for nobody, so what its device does later reaches nothing.

    Stopping waits a while for the worker, and a device slow to open can keep it longer. A song taking the
    device stops the manager's playback first, so the worker can meet a refusal while the song plays.
    """

    LENGTH: Final[int] = 8

    @pytest.fixture(name="let_go")
    def let_go_fixture(self) -> Tuple[AudioDeviceManager, Dict[str, Any]]:
        """A stopped manager, and the arguments the worker of its stopped playback was started with."""
        manager = _manager()
        manager._buffer_size = self.LENGTH
        manager._position_callback = MagicMock()
        manager._playback_thread = None
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(self.LENGTH, dtype=np.float32))
            manager.stop()

        manager._position_callback.reset_mock()
        return manager, thread.call_args.kwargs["kwargs"]

    def test_a_refusal_it_meets_later_reports_nothing_and_resets_nothing(
        self,
        let_go: Tuple[AudioDeviceManager, Dict[str, Any]],
    ) -> None:
        manager, worker = let_go
        _refusing(manager, "the device is busy")
        reported: List[Exception] = []
        manager.on_playback_error = reported.append

        manager._playback_worker(**worker)

        assert reported == []
        manager._position_callback.assert_not_called()

    def test_a_stream_it_opens_later_closes_unplayed(self, let_go: Tuple[AudioDeviceManager, Dict[str, Any]]) -> None:
        manager, worker = let_go

        manager._playback_worker(**worker)

        assert _closed_unplayed(_system(manager))
        manager._position_callback.assert_not_called()

    def test_a_playback_started_after_the_stop_stands(self, let_go: Tuple[AudioDeviceManager, Dict[str, Any]]) -> None:
        """The worker let go of leaves the playback asked for after it as it is."""
        manager, worker = let_go
        _refusing(manager, "the device is busy")
        reported: List[Exception] = []
        manager.on_playback_error = reported.append
        with patch("sampletones_core.audio.manager.threading.Thread"):
            manager.play(np.ones(self.LENGTH, dtype=np.float32))

        manager._playback_worker(**worker)

        assert manager.is_playing()
        assert reported == []


class TestSeekingAPlayback(BaseTestSuite):
    """A seek moves the playback of the owner asking for it, clamped to the audio, under one lock."""

    AUDIO_LENGTH: Final[int] = 8

    @staticmethod
    def _playing(owner: object, length: int) -> AudioDeviceManager:
        manager = _manager()
        manager._audio_data = np.zeros(length, dtype=np.float32)
        manager._playing = True
        manager._output_owner = owner
        return manager

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        position: int
        expected: int

    test_cases = (
        TestCase(position=5, expected=5, label="within_the_audio"),
        TestCase(position=-3, expected=0, label="before_the_audio_clamps_to_its_beginning"),
        TestCase(position=AUDIO_LENGTH + 4, expected=AUDIO_LENGTH, label="past_the_audio_clamps_to_its_end"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_owner_moves_its_playback(self, test_case: TestCase) -> None:
        owner = object()
        manager = self._playing(owner, self.AUDIO_LENGTH)

        moved = manager.set_position(test_case.position, owner=owner)

        assert (moved, manager.position_of(owner)) == (True, test_case.expected)

    def test_another_owner_leaves_the_playback_where_it_stands(self) -> None:
        owner = object()
        manager = self._playing(owner, self.AUDIO_LENGTH)
        manager._position = 3

        moved = manager.set_position(5, owner=object())

        assert (moved, manager.position_of(owner)) == (False, 3)


class TestOwnership:
    """Ownership tells a source's own playback apart from a preview or another source's output."""

    def test_owned_while_playing_and_owner_matches(self) -> None:
        manager = _manager()
        owner = object()
        manager._output_owner = owner
        manager._playing = True

        assert manager.is_owned_by(owner) is True

    def test_not_owned_when_idle(self) -> None:
        manager = _manager()
        owner = object()
        manager._output_owner = owner
        manager._playing = False

        assert manager.is_owned_by(owner) is False

    def test_not_owned_by_a_different_owner(self) -> None:
        manager = _manager()
        manager._output_owner = object()
        manager._playing = True

        assert manager.is_owned_by(object()) is False

    def test_preview_owned_by_nobody_is_not_owned_by_a_source(self) -> None:
        manager = _manager()
        manager._output_owner = None
        manager._playing = True

        assert manager.is_owned_by(object()) is False


class TestPositionOfAnOwner:
    """A source reads where its own playback stands, and the start of the audio for anyone else's."""

    def test_the_owner_reads_the_position_its_playback_reached(self) -> None:
        manager = _manager()
        owner = object()
        manager._output_owner = owner
        manager._playing = True
        manager._position = 640

        assert manager.position_of(owner) == 640

    def test_another_source_reads_the_start_of_the_audio(self) -> None:
        manager = _manager()
        manager._output_owner = object()
        manager._playing = True
        manager._position = 640

        assert manager.position_of(object()) == START_OF_AUDIO

    def test_an_owner_whose_playback_ended_reads_the_start_of_the_audio(self) -> None:
        manager = _manager()
        owner = object()
        manager._output_owner = owner
        manager._playing = False
        manager._position = 640

        assert manager.position_of(owner) == START_OF_AUDIO


class TestBackendTeardown:
    """The backend is torn down only once every stream opened under a lease has come back."""

    def test_a_stream_is_outstanding_until_its_lease_comes_back(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        lease = manager.acquire_output(priority=_LOW, release=MagicMock())
        assert lease is not None
        stream = manager.open_output_stream(lease, sample_rate=48000, buffer_size=800)
        assert stream is not None
        assert manager._outstanding == [lease]

        manager.hand_back(lease)

        assert (manager._claims, manager._outstanding, lease.stream) == ([], [], None)
        timeline = _system(manager).timeline
        assert len(timeline.of(Drained)) == 1
        assert len(timeline.of(Closed)) == 1

    def test_terminate_releases_a_lease_first(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        system = _system(manager)
        _streaming_holder(manager, _LOW)

        manager.terminate()

        assert [type(event) for event in system.timeline.events() if isinstance(event, (Closed, Terminated))] == [
            Closed,
            Terminated,
        ]
        assert manager._driver is None

    def test_terminate_keeps_the_backend_while_a_stream_outlives_its_release(self) -> None:
        manager = _holding_manager(lambda: None)
        driver = manager._driver

        manager.terminate()

        assert _system(manager).timeline.of(Terminated) == []
        assert manager._driver is driver

    def test_reinitialize_refuses_while_a_stream_outlives_its_release(self) -> None:
        manager = _holding_manager(lambda: None)
        driver = manager._driver

        with pytest.raises(PlaybackError):
            manager.reinitialize()

        assert _system(manager).timeline.of(Terminated) == []
        assert manager._driver is driver

    def test_a_release_may_hand_its_lease_back_from_the_writing_thread(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        holder = _streaming_holder(manager, _LOW)

        manager.terminate()

        assert holder.handed_back.is_set()
        assert manager._driver is None


class TestOutputLeases(BaseTestSuite):
    """A lease claims the output from the moment a source asks to play until it is handed back.

    A claim is ranked against every holder in force: one ranked strictly below is declined and
    releases nobody, and an equal or higher one takes the output over and asks each other holder to
    hand its lease back. A lease that lost the output opens no stream, and the backend declines
    every claim while it is reconfigured or torn down.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        held: int
        asked: int
        granted: bool

    test_cases = (
        TestCase(held=_HIGH, asked=_LOW, granted=False, label="a_claim_below_the_holder_is_declined"),
        TestCase(held=_LOW, asked=_LOW, granted=True, label="an_equal_claim_takes_the_output_over"),
        TestCase(held=_LOW, asked=_HIGH, granted=True, label="a_higher_claim_takes_the_output_over"),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_claim_is_ranked_against_the_holder(self, test_case: TestCase) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        holder = _streaming_holder(manager, test_case.held)

        lease = manager.acquire_output(priority=test_case.asked, release=MagicMock())

        assert (lease is not None) is test_case.granted
        assert holder.handed_back.is_set() is test_case.granted
        assert holder.releases == int(test_case.granted)

    def test_a_claim_below_buffer_playback_is_declined(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        manager._playing = True
        manager._active_priority = _HIGH

        lease = manager.acquire_output(priority=_LOW, release=MagicMock())

        assert lease is None
        manager.stop.assert_not_called()

    def test_a_lease_that_lost_the_output_opens_nothing(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        first = manager.acquire_output(priority=_LOW, release=MagicMock())
        assert first is not None
        manager.acquire_output(priority=_LOW, release=MagicMock())

        stream = manager.open_output_stream(first, sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800)

        assert stream is None
        assert _system(manager).timeline.of(Opened) == []

    def test_a_lease_that_lost_the_output_while_opening_closes_what_it_opened(self) -> None:
        """A device slow to open lets another claim land meanwhile; the stream opened late closes unplayed."""
        manager = _manager()
        manager.stop = MagicMock()
        first = manager.acquire_output(priority=_LOW, release=MagicMock())
        assert first is not None
        system = _system(manager)

        def open_while_another_claims(_call: OpenCall) -> None:
            system.hooks.before_open = None
            manager.acquire_output(priority=_LOW, release=MagicMock())

        system.hooks.before_open = open_while_another_claims

        stream = manager.open_output_stream(first, sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800)

        assert stream is None
        assert _closed_unplayed(system)
        assert manager._outstanding == []

    def test_two_claims_at_once_leave_one_holder(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        barrier = threading.Barrier(2)
        holders = [_Holder(manager), _Holder(manager)]

        def claim(holder: _Holder) -> None:
            barrier.wait(timeout=_RELEASE_TIMEOUT)
            holder.claim(_LOW)

        threads = [threading.Thread(target=claim, args=(holder,), daemon=True) for holder in holders]
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=_RELEASE_TIMEOUT)

        assert len(manager._claims) == 1
        assert sum(holder.releases for holder in holders) == 1

    def test_a_claim_while_the_device_changes_is_declined(self) -> None:
        """A holder asking again from inside its release meets the closed output, and the switch goes through."""
        manager = _manager()
        manager.stop = MagicMock()
        holder = _streaming_holder(manager, _LOW)
        claims_during_the_switch: List[Optional[OutputLease]] = []
        holder_release = holder.release

        def release_then_claim() -> None:
            holder_release()
            claims_during_the_switch.append(manager.acquire_output(priority=_LOW, release=MagicMock()))

        assert holder.lease is not None
        holder.lease.release = release_then_claim

        manager.configure_device(_SPEAKERS_INDEX, DEFAULT_SAMPLE_RATE)

        assert claims_during_the_switch == [None]
        assert manager.acquire_output(priority=_LOW, release=MagicMock()) is not None

    def test_a_device_change_releases_every_lease(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        holder = _streaming_holder(manager, _LOW)

        manager.configure_device(_SPEAKERS_INDEX, DEFAULT_SAMPLE_RATE)

        assert holder.handed_back.is_set()
        assert (manager._claims, manager._outstanding) == ([], [])

    def test_a_claim_after_teardown_is_declined(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        manager.terminate()

        assert manager.acquire_output(priority=_HIGH, release=MagicMock()) is None

    def test_a_lease_handed_back_unopened_leaves_nothing_outstanding(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        lease = manager.acquire_output(priority=_LOW, release=MagicMock())
        assert lease is not None

        manager.hand_back(lease)

        assert (manager._claims, manager._outstanding) == ([], [])
        assert manager.acquire_output(priority=_LOW, release=MagicMock()) is not None


class TestTeardownAfterAStopLetAWorkerGo:
    """Teardown waits for a worker a stop let go of, so the backend goes once nothing reaches into it.

    A device slow to open keeps the worker past the stop's wait, and terminating the backend under an
    open in progress pulls it from under the worker.
    """

    LENGTH: Final[int] = 8

    @pytest.fixture(name="slow_open")
    def slow_open_fixture(self) -> Iterator[Tuple[AudioDeviceManager, threading.Event]]:
        """A manager whose playback a stop let go of while its stream opens, and the open's gate."""
        opening = threading.Event()
        manager = _manager()
        manager._buffer_size = self.LENGTH
        manager._position_callback = None
        manager._playback_thread = None
        manager.on_playback_error = None
        _system(manager).hooks.before_open = lambda _call: opening.wait(timeout=_RELEASE_TIMEOUT)
        manager.play(np.zeros(self.LENGTH, dtype=np.float32))
        with patch(_STOP_JOIN_TARGET, _SHORT_JOIN):
            manager.stop()

        yield manager, opening
        opening.set()

    @staticmethod
    def milestones(manager_system: FakeAudioSystem) -> List[type]:
        """The opens and the terminations the device met, in order."""
        return [type(event) for event in manager_system.timeline.events() if isinstance(event, (Opened, Terminated))]

    def test_terminate_waits_for_the_worker_to_finish_its_open(
        self,
        slow_open: Tuple[AudioDeviceManager, threading.Event],
    ) -> None:
        manager, opening = slow_open
        system = _system(manager)
        releaser = threading.Timer(_OPEN_DELAY, opening.set)
        releaser.start()
        try:
            manager.terminate()
        finally:
            releaser.cancel()
            opening.set()

        assert self.milestones(system) == [Opened, Terminated]
        assert system.timeline.violations() == []
        assert manager._driver is None

    def test_terminate_keeps_the_backend_while_the_worker_outlives_the_wait(
        self,
        slow_open: Tuple[AudioDeviceManager, threading.Event],
    ) -> None:
        manager, _ = slow_open
        system = _system(manager)
        driver = manager._driver

        with patch(_LET_GO_JOIN_TARGET, _SHORT_JOIN):
            manager.terminate()

        assert self.milestones(system) == []
        assert manager._driver is driver

    def test_reinitialize_refuses_while_the_worker_outlives_the_wait(
        self,
        slow_open: Tuple[AudioDeviceManager, threading.Event],
    ) -> None:
        manager, _ = slow_open
        system = _system(manager)
        driver = manager._driver

        with patch(_LET_GO_JOIN_TARGET, _SHORT_JOIN), pytest.raises(PlaybackError):
            manager.reinitialize()

        assert self.milestones(system) == []
        assert manager._driver is driver


@pytest.fixture(name="system")
def system_fixture() -> FakeAudioSystem:
    """A machine offering one pair of speakers as its default output."""
    return ticking_machine([SPEAKERS], default_device=_SPEAKERS_INDEX)


@pytest.fixture(name="silent_system")
def silent_system_fixture() -> FakeAudioSystem:
    """A machine offering no output device at all."""
    return ticking_machine([], default_device=None)


class TestCurrentDevice:
    """The device in force reads as ``None`` wherever nothing is selected.

    A machine offering no output device starts with nothing selected, and a refresh that takes the
    selected device off the list leaves nothing selected too. Each answers ``None``, where a machine
    with a device answers the device and the rate it plays at.
    """

    def test_the_default_device_is_in_force(self, system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(system.driver)

        assert manager.get_current_device() == CurrentDevice(
            device_index=_SPEAKERS_INDEX,
            name=SPEAKERS.name,
            sample_rate=SPEAKERS.default_sample_rate,
            host_api=SPEAKERS.host_api,
        )

    def test_a_machine_offering_no_device_has_none_in_force(self, silent_system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(silent_system.driver)

        assert manager.list_devices() == {}
        assert manager.get_current_device() is None

    def test_a_device_taken_off_the_list_leaves_none_in_force(self, system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(system.driver)
        assert manager.get_current_device() is not None

        system.devices = []
        manager.refresh_devices()

        assert manager.get_current_device() is None

    def test_configuring_answers_the_device_now_in_force(self, system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(system.driver)

        configured = manager.configure_device(_SPEAKERS_INDEX, _CHOSEN_RATE)

        assert configured.sample_rate == _CHOSEN_RATE
        assert manager.get_current_device() == configured


class TestPlayingWithNoOutput:
    """Every way to start a sound asks the manager for the output first, and with none in force the
    manager refuses at once, before a thread or a stream starts.

    Each refusal is the typed ``NoOutputDeviceError``, which every recovery boundary catches as a
    ``PlaybackError``. A machine offering speakers answers the device and rate the stream opens on.
    """

    @pytest.fixture(name="silent_manager")
    def silent_manager_fixture(self, silent_system: FakeAudioSystem) -> AudioDeviceManager:
        """A manager on a machine offering no output device."""
        return AudioDeviceManager(silent_system.driver)

    def test_a_device_in_force_answers_what_the_stream_opens_on(self, system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(system.driver)

        assert manager.require_output() == manager.get_current_device()

    def test_asking_for_the_output_is_refused(self, silent_manager: AudioDeviceManager) -> None:
        with pytest.raises(NoOutputDeviceError):
            silent_manager.require_output()

    def test_a_refusal_is_a_playback_error(self) -> None:
        assert issubclass(NoOutputDeviceError, PlaybackError)

    def test_playing_audio_is_refused_before_a_thread_starts(self, silent_manager: AudioDeviceManager) -> None:
        with (
            patch("sampletones_core.audio.manager.threading.Thread") as thread,
            pytest.raises(NoOutputDeviceError),
        ):
            silent_manager.play(np.zeros(4, dtype=np.float32), priority=_HIGH)

        thread.assert_not_called()
        assert silent_manager.is_playing() is False

    def test_playing_a_file_is_refused_before_the_file_is_read(self, silent_manager: AudioDeviceManager) -> None:
        with (
            patch(_LOAD_AUDIO) as load_audio,
            pytest.raises(NoOutputDeviceError),
        ):
            silent_manager.play_file(Path(_AUDIO_FILE))

        load_audio.assert_not_called()

    def test_a_stream_is_refused_before_it_opens(
        self,
        silent_manager: AudioDeviceManager,
        silent_system: FakeAudioSystem,
    ) -> None:
        with pytest.raises(NoOutputDeviceError):
            silent_manager.acquire_output(priority=_LOW, release=MagicMock())

        assert silent_system.timeline.of(Opened) == []
        assert silent_manager._claims == []

    def test_the_rate_reads_as_the_same_refusal(self, silent_manager: AudioDeviceManager) -> None:
        with pytest.raises(NoOutputDeviceError):
            _ = silent_manager.sample_rate

    def test_a_device_taken_off_the_list_refuses_a_playback(self, system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(system.driver)
        system.devices = []
        manager.refresh_devices()

        with (
            patch("sampletones_core.audio.manager.threading.Thread") as thread,
            pytest.raises(NoOutputDeviceError),
        ):
            manager.play(np.zeros(4, dtype=np.float32))

        thread.assert_not_called()

    def test_a_playback_opens_its_stream_on_the_device_in_force(self, system: FakeAudioSystem) -> None:
        manager = AudioDeviceManager(system.driver)
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(4, dtype=np.float32))

        assert thread.call_args.kwargs["kwargs"]["output"] == manager.get_current_device()
