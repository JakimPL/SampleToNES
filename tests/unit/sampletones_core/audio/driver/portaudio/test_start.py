from typing import Final

import pyaudio
import pytest

from sampletones_core.audio.driver import UnstartedDriver
from sampletones_core.audio.driver.portaudio import start
from sampletones_core.audio.driver.portaudio.start import start_portaudio
from tests.suite.base import BaseTestSuite

UNANTICIPATED_HOST_ERROR: Final[int] = -9999


class StartedDriver:
    """The PortAudio driver as it stands once PortAudio started."""


def _refuse_to_start(audio: pyaudio.PyAudio) -> None:
    raise OSError(UNANTICIPATED_HOST_ERROR, "Unanticipated host error")


class TestStartingPortAudio(BaseTestSuite):
    """PortAudio starts as the backend where it can, and the backend listing no device stands in where it refuses."""

    def test_a_started_portaudio_is_the_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(start, "PyAudioDriver", StartedDriver)

        assert isinstance(start_portaudio(), StartedDriver)

    def test_a_refused_start_leaves_a_backend_listing_no_device(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(pyaudio.PyAudio, "__init__", _refuse_to_start)

        driver = start_portaudio()

        assert isinstance(driver, UnstartedDriver)
        assert driver.device_count() == 0

    def test_every_start_asks_portaudio_again(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A refresh starts the backend anew, so an audio system that came up since is found."""
        monkeypatch.setattr(pyaudio.PyAudio, "__init__", _refuse_to_start)
        assert isinstance(start_portaudio(), UnstartedDriver)

        monkeypatch.setattr(start, "PyAudioDriver", StartedDriver)
        assert isinstance(start_portaudio(), StartedDriver)
