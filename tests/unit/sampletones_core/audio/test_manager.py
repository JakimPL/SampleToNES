import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Final, Iterator, List, Tuple, Union
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_core.audio.device import AudioDevice, CurrentDevice
from sampletones_core.audio.manager import AudioDeviceManager
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO, SampleRate
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

_LOW = 0
_HIGH = 1
_RELEASE_TIMEOUT: Final[float] = 5.0
_BACKEND: Final[str] = "sampletones_core.audio.manager.pyaudio.PyAudio"
_SPEAKERS_INDEX: Final[int] = 0
_SPEAKERS_NAME: Final[str] = "Speakers"
_SPEAKERS_HOST_API: Final[int] = 2
_CHOSEN_RATE: Final[SampleRate] = 48000
_SPEAKERS: Final[Dict[str, Union[int, str]]] = {
    "index": _SPEAKERS_INDEX,
    "name": _SPEAKERS_NAME,
    "maxOutputChannels": 2,
    "defaultSampleRate": DEFAULT_SAMPLE_RATE,
    "hostApi": _SPEAKERS_HOST_API,
}
_SPEAKERS_DEVICE: Final[AudioDevice] = AudioDevice(
    index=_SPEAKERS_INDEX,
    name=_SPEAKERS_NAME,
    default_sample_rate=DEFAULT_SAMPLE_RATE,
    supported_sample_rates=[DEFAULT_SAMPLE_RATE],
    host_api=_SPEAKERS_HOST_API,
)
_AUDIO_FILE: Final[str] = "recording.wav"
_LOAD_AUDIO: Final[str] = "sampletones_core.audio.manager.load_audio"


def _manager() -> AudioDeviceManager:
    """A manager with only the state the playback-coordination paths touch.

    The full constructor enumerates real audio hardware via PyAudio; that is irrelevant to the
    single-output priority arbitration under test here.
    """
    manager = object.__new__(AudioDeviceManager)
    manager._pyaudio = MagicMock()
    manager._devices = {_SPEAKERS_INDEX: _SPEAKERS_DEVICE}
    manager._device_index = _SPEAKERS_INDEX
    manager._sample_rate = DEFAULT_SAMPLE_RATE
    manager._lock = threading.Lock()
    manager._resume_event = threading.Event()
    manager._playing = False
    manager._active_priority = 0
    manager._generation = 0
    manager._stream_owners = {}
    manager.on_acquire_output = None
    manager.external_output_priority = None
    return manager


def _holding_manager(release: Callable[[], None]) -> AudioDeviceManager:
    """A manager that handed out one output stream against ``release``."""
    manager = _manager()
    manager.stop = MagicMock()
    manager._stream_owners = {MagicMock(): release}
    return manager


class _ThreadedOwner:
    """A stream owner that hands its stream back from the thread that was writing to it.

    Mirrors the song player: the release runs on the caller's thread while the hand-back comes
    from the writer, so the two meet only while the manager holds no lock across a release.
    """

    def __init__(self, manager: AudioDeviceManager, stream: MagicMock) -> None:
        self._manager = manager
        self._stream = stream
        self.handed_back = threading.Event()

    def release(self) -> None:
        writer = threading.Thread(target=self._hand_back, daemon=True)
        writer.start()
        writer.join(timeout=_RELEASE_TIMEOUT)

    def _hand_back(self) -> None:
        self._manager.close_output_stream(self._stream)
        self.handed_back.set()


class TestSingleOutputExclusion:
    """The output device allows one open stream, so the two playback paths must release each other."""

    def test_open_output_stream_stops_internal_playback(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()

        manager.open_output_stream(sample_rate=48000, buffer_size=800, release=MagicMock())

        manager.stop.assert_called_once()
        manager._pyaudio.open.assert_called_once()

    def test_play_releases_active_external_output(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        manager.on_acquire_output = MagicMock()
        manager.external_output_priority = lambda: _HIGH

        with patch("sampletones_core.audio.manager.threading.Thread"):
            manager.play(np.zeros(4, dtype=np.float32), priority=_HIGH)

        manager.on_acquire_output.assert_called_once()


class TestPriorityArbitration:
    """A lower-priority request yields to active higher-priority playback; ties take over."""

    def test_yields_to_higher_external_priority(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        manager.external_output_priority = lambda: _HIGH

        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(4, dtype=np.float32), priority=_LOW)

        thread.assert_not_called()
        manager.stop.assert_not_called()

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
        manager._pyaudio.open.side_effect = OSError("the device is busy")
        manager._position_callback = MagicMock()
        playing_when_reported: List[bool] = []
        manager.on_playback_error = lambda _error: playing_when_reported.append(manager.is_playing())
        manager._playing = True
        manager._audio_data = np.zeros(TestPlaybackStart.AUDIO_LENGTH, dtype=np.float32)

        manager._playback_worker(output=manager.require_output(), update=True, generation=manager._generation)

        assert playing_when_reported == [False]
        manager._position_callback.assert_called_once_with(0)

    def test_a_handed_out_stream_refused_raises_a_playback_error(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        manager._pyaudio.open.side_effect = OSError("the device is busy")

        with pytest.raises(PlaybackError, match="the device is busy"):
            manager.open_output_stream(sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800, release=MagicMock())

        assert manager._stream_owners == {}

    def test_both_kinds_of_playback_name_the_refusal_alike(self) -> None:
        """A refused stream reads the same whether the manager plays the audio or hands the stream out."""
        manager = _manager()
        manager.stop = MagicMock()
        manager._pyaudio.open.side_effect = OSError("the device is busy")
        manager._position_callback = None
        reported: List[Exception] = []
        manager.on_playback_error = reported.append
        manager._playing = True
        manager._audio_data = np.zeros(TestPlaybackStart.AUDIO_LENGTH, dtype=np.float32)
        manager._playback_worker(output=manager.require_output(), update=False, generation=manager._generation)

        with pytest.raises(PlaybackError) as raised:
            manager.open_output_stream(sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800, release=MagicMock())

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
        manager._pyaudio.open.side_effect = OSError("the device is busy")
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
        stream = MagicMock()
        manager._pyaudio.open.return_value = stream

        manager._playback_worker(**first_worker)

        stream.write.assert_not_called()
        stream.close.assert_called_once_with()
        self.assert_the_newer_playback_stands(manager)

    def test_the_newer_worker_refused_reports_it(
        self,
        replaced: Tuple[AudioDeviceManager, Dict[str, Any]],
    ) -> None:
        """The refusal of the playback in force still reaches the reader."""
        manager, _ = replaced
        manager._pyaudio.open.side_effect = OSError("the device is busy")
        reported: List[Exception] = []
        manager.on_playback_error = reported.append
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.ones(self.SECOND_LENGTH, dtype=np.float32))

        manager._playback_worker(**thread.call_args.kwargs["kwargs"])

        assert len(reported) == 1
        assert not manager.is_playing()


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
    """The backend is torn down only once every handed-out stream has come back."""

    def test_a_handed_out_stream_is_outstanding_until_it_comes_back(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        stream = manager.open_output_stream(sample_rate=48000, buffer_size=800, release=MagicMock())
        assert stream in manager._stream_owners

        manager.close_output_stream(stream)

        assert manager._stream_owners == {}
        stream.stop_stream.assert_called_once()
        stream.close.assert_called_once()

    def test_terminate_releases_a_handed_out_stream_first(self) -> None:
        events: List[str] = []
        manager = _manager()
        manager.stop = MagicMock()
        instance = manager._pyaudio
        instance.terminate.side_effect = lambda: events.append("terminate")
        stream = MagicMock()

        def release() -> None:
            events.append("release")
            manager.close_output_stream(stream)

        manager._stream_owners = {stream: release}
        manager.terminate()

        assert events == ["release", "terminate"]
        assert manager._pyaudio is None

    def test_terminate_keeps_the_backend_while_a_stream_outlives_its_release(self) -> None:
        manager = _holding_manager(lambda: None)
        instance = manager._pyaudio

        manager.terminate()

        instance.terminate.assert_not_called()
        assert manager._pyaudio is instance

    def test_reinitialize_refuses_while_a_stream_outlives_its_release(self) -> None:
        manager = _holding_manager(lambda: None)
        instance = manager._pyaudio

        with pytest.raises(PlaybackError):
            manager.reinitialize()

        instance.terminate.assert_not_called()
        assert manager._pyaudio is instance

    def test_a_release_may_hand_its_stream_back_from_the_writing_thread(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()
        stream = MagicMock()
        owner = _ThreadedOwner(manager, stream)
        manager._stream_owners = {stream: owner.release}

        manager.terminate()

        assert owner.handed_back.is_set()
        assert manager._pyaudio is None


@pytest.fixture(name="backend")
def backend_fixture() -> Iterator[MagicMock]:
    """The audio backend of a machine offering one pair of speakers as its default output."""
    with patch(_BACKEND) as backend_class:
        backend = backend_class.return_value
        backend.get_device_count.return_value = 1
        backend.get_device_info_by_index.return_value = _SPEAKERS
        backend.get_default_output_device_info.return_value = _SPEAKERS
        yield backend


@pytest.fixture(name="silent_backend")
def silent_backend_fixture() -> Iterator[MagicMock]:
    """The audio backend of a machine offering no output device at all."""
    with patch(_BACKEND) as backend_class:
        backend = backend_class.return_value
        backend.get_device_count.return_value = 0
        backend.get_default_output_device_info.side_effect = OSError
        yield backend


class TestCurrentDevice:
    """The device in force reads as ``None`` wherever nothing is selected.

    A machine offering no output device starts with nothing selected, and a refresh that takes the
    selected device off the list leaves nothing selected too. Each answers ``None``, where a machine
    with a device answers the device and the rate it plays at.
    """

    def test_the_default_device_is_in_force(self, backend: MagicMock) -> None:
        manager = AudioDeviceManager()

        assert manager.get_current_device() == CurrentDevice(
            device_index=_SPEAKERS_INDEX,
            name=_SPEAKERS_NAME,
            sample_rate=DEFAULT_SAMPLE_RATE,
            host_api=_SPEAKERS_HOST_API,
        )

    def test_a_machine_offering_no_device_has_none_in_force(self, silent_backend: MagicMock) -> None:
        manager = AudioDeviceManager()

        assert manager.list_devices() == {}
        assert manager.get_current_device() is None

    def test_a_device_taken_off_the_list_leaves_none_in_force(self, backend: MagicMock) -> None:
        manager = AudioDeviceManager()
        assert manager.get_current_device() is not None

        backend.get_device_count.return_value = 0
        manager.refresh_devices()

        assert manager.get_current_device() is None

    def test_configuring_answers_the_device_now_in_force(self, backend: MagicMock) -> None:
        manager = AudioDeviceManager()

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
    def silent_manager_fixture(self, silent_backend: MagicMock) -> AudioDeviceManager:
        """A manager on a machine offering no output device."""
        return AudioDeviceManager()

    def test_a_device_in_force_answers_what_the_stream_opens_on(self, backend: MagicMock) -> None:
        manager = AudioDeviceManager()

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
        silent_backend: MagicMock,
    ) -> None:
        with pytest.raises(NoOutputDeviceError):
            silent_manager.open_output_stream(sample_rate=DEFAULT_SAMPLE_RATE, buffer_size=800, release=MagicMock())

        silent_backend.open.assert_not_called()
        assert silent_manager._stream_owners == {}

    def test_the_rate_reads_as_the_same_refusal(self, silent_manager: AudioDeviceManager) -> None:
        with pytest.raises(NoOutputDeviceError):
            _ = silent_manager.sample_rate

    def test_a_device_taken_off_the_list_refuses_a_playback(self, backend: MagicMock) -> None:
        manager = AudioDeviceManager()
        backend.get_device_count.return_value = 0
        manager.refresh_devices()

        with (
            patch("sampletones_core.audio.manager.threading.Thread") as thread,
            pytest.raises(NoOutputDeviceError),
        ):
            manager.play(np.zeros(4, dtype=np.float32))

        thread.assert_not_called()

    def test_a_playback_opens_its_stream_on_the_device_in_force(self, backend: MagicMock) -> None:
        manager = AudioDeviceManager()
        with patch("sampletones_core.audio.manager.threading.Thread") as thread:
            manager.play(np.zeros(4, dtype=np.float32))

        assert thread.call_args.kwargs["kwargs"]["output"] == manager.get_current_device()
