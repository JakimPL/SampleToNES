import threading
from typing import Callable, Final, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_core.audio.manager import AudioDeviceManager
from sampletones_shared.exceptions import PlaybackError

_LOW = 0
_HIGH = 1
_RELEASE_TIMEOUT: Final[float] = 5.0


def _manager() -> AudioDeviceManager:
    """A manager with only the state the playback-coordination paths touch.

    The full constructor enumerates real audio hardware via PyAudio; that is irrelevant to the
    single-output priority arbitration under test here.
    """
    manager = object.__new__(AudioDeviceManager)
    manager._pyaudio = MagicMock()
    manager._device_index = 0
    manager._lock = threading.Lock()
    manager._resume_event = threading.Event()
    manager._playing = False
    manager._active_priority = 0
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
