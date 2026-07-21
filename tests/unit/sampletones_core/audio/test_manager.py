import threading
from unittest.mock import MagicMock, patch

import numpy as np

from sampletones_core.audio.manager import AudioDeviceManager

_LOW = 0
_HIGH = 1


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
    manager.on_acquire_output = None
    manager.external_output_priority = None
    return manager


class TestSingleOutputExclusion:
    """The output device allows one open stream, so the two playback paths must release each other."""

    def test_open_output_stream_stops_internal_playback(self) -> None:
        manager = _manager()
        manager.stop = MagicMock()

        manager.open_output_stream(sample_rate=48000, buffer_size=800)

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
