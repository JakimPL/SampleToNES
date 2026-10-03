import threading
from enum import StrEnum
from pathlib import Path
from typing import Final, Optional

import numpy as np
import pyaudio
import pytest

ALSA_CONFIGURATION_FILE: Final[str] = ".asoundrc"
SILENT_DEFAULT_DEVICE: Final[str] = "pcm.!default {\n    type null\n}\n"


class OutputDevice(StrEnum):
    """The output a scenario's machine offers: a device that plays into silence, or none at all."""

    SILENT = "silent"
    NONE = "none"


class OutputRecord:
    """What the application wrote to its output device: how many of the samples it played carry sound.

    It wraps the write of every output stream, so a sound counts once it reaches the device, however briefly it
    plays and however many frames pass between two readings of it. The playback thread writes while a
    scenario reads, so the count stands behind a lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sounding_samples = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Puts the record in front of every output stream's write before the application starts.

        ``PyAudio.open`` builds its streams from ``PyAudio.Stream``, the class whose write is wrapped.
        """
        write = pyaudio.PyAudio.Stream.write

        def recorded(
            stream: pyaudio.PyAudio.Stream,
            frames: bytes,
            num_frames: Optional[int] = None,
            exception_on_underflow: bool = False,
        ) -> None:
            self._count(frames)
            write(stream, frames, num_frames, exception_on_underflow)

        monkeypatch.setattr(pyaudio.PyAudio.Stream, "write", recorded)

    def sounding_samples(self) -> int:
        """How many samples carrying sound the application has written to its output so far."""
        with self._lock:
            return self._sounding_samples

    def _count(self, frames: bytes) -> None:
        sounding = int(np.count_nonzero(np.frombuffer(frames, dtype=np.float32)))
        with self._lock:
            self._sounding_samples += sounding


def provide_output_device(
    device: OutputDevice,
    *,
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gives the application the output ``device`` before it starts."""
    match device:
        case OutputDevice.SILENT:
            _silent_output_device(home)
        case OutputDevice.NONE:
            _no_output_device(monkeypatch)


def _silent_output_device(home: Path) -> None:
    """Points ALSA's default device at a sink that consumes sound in real time and plays none of it.

    Playback runs as it does for a user, its stream and its cursor included, and nothing is heard.
    """
    (home / ALSA_CONFIGURATION_FILE).write_text(SILENT_DEFAULT_DEVICE, encoding="utf-8")


def _no_output_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starts the application on a machine offering no output device at all."""
    monkeypatch.setattr(pyaudio.PyAudio, "get_device_count", lambda _: 0)
    monkeypatch.setattr(pyaudio.PyAudio, "get_default_output_device_info", _no_default_device)


def _no_default_device(_: pyaudio.PyAudio) -> None:
    raise OSError("A screen scenario offers no output device")
