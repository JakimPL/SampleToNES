import threading
import time
from enum import StrEnum
from pathlib import Path
from typing import Final, Optional
from weakref import WeakKeyDictionary

import numpy as np
import pyaudio
import pytest

ALSA_CONFIGURATION_FILE: Final[str] = ".asound.conf"
ALSA_CONFIGURATION_VARIABLE: Final[str] = "ALSA_CONFIG_PATH"
DEVICE_BUFFER_SECONDS: Final[float] = 0.05
SILENT_DEFAULT_DEVICE: Final[str] = "pcm.!default {\n    type null\n}\n"
REFUSED_STREAM: Final[str] = "A screen scenario's device refuses every stream"


class OutputDevice(StrEnum):
    """The output a scenario's machine offers: a device that plays into silence, one that refuses every
    stream, or none at all."""

    SILENT = "silent"
    REFUSING = "refusing"
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


class DeviceClock:
    """Plays a stream's sound out at its rate: a write returns once what it hands over fits the buffer, and a
    stop once the buffer has played out.

    The buffer keeps ``DEVICE_BUFFER_SECONDS`` of sound waiting, as a device's does. Sound written once the
    buffer has run dry starts playing as it arrives, as it does on a device that underran.
    """

    def __init__(self, bytes_per_second: int) -> None:
        self._bytes_per_second = bytes_per_second
        self._played_out_at = time.monotonic()

    def write(self, frames: bytes) -> None:
        """Returns once ``frames`` fit in the buffer, the moment a device's blocking write returns."""
        now = time.monotonic()
        self._played_out_at = max(self._played_out_at, now) + len(frames) / self._bytes_per_second
        time.sleep(max(0.0, self._played_out_at - DEVICE_BUFFER_SECONDS - now))

    def drain(self) -> None:
        """Returns once the sound written has played out, the moment a device's stop returns."""
        time.sleep(max(0.0, self._played_out_at - time.monotonic()))


class SilentOutputDevice:
    """The one output device a scenario's application finds: ALSA's null sink, played out in real time.

    The scenario's ALSA reads a configuration of its own, which names the null sink its default device and
    leaves the machine's sound cards and sound server out, so every machine offers the same device and plays
    into silence. The null sink takes sound as fast as it comes, so a clock behind each output stream returns
    a write and a stop when a device would.
    """

    def __init__(self) -> None:
        self._clocks: WeakKeyDictionary[pyaudio.PyAudio.Stream, DeviceClock] = WeakKeyDictionary()

    def install(self, home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Points ALSA at the null sink and puts a clock behind every stream before the application starts."""
        configuration = home / ALSA_CONFIGURATION_FILE
        configuration.write_text(SILENT_DEFAULT_DEVICE, encoding="utf-8")
        monkeypatch.setenv(ALSA_CONFIGURATION_VARIABLE, str(configuration))

        open_stream = pyaudio.PyAudio.open
        write = pyaudio.PyAudio.Stream.write
        stop_stream = pyaudio.PyAudio.Stream.stop_stream

        def opened(
            audio: pyaudio.PyAudio,
            *,
            rate: int,
            channels: int,
            format: int,  # pylint: disable=redefined-builtin
            **options: object,
        ) -> pyaudio.PyAudio.Stream:
            stream = open_stream(audio, rate=rate, channels=channels, format=format, **options)
            self._clocks[stream] = DeviceClock(rate * channels * pyaudio.get_sample_size(format))
            return stream

        def played(
            stream: pyaudio.PyAudio.Stream,
            frames: bytes,
            num_frames: Optional[int] = None,
            exception_on_underflow: bool = False,
        ) -> None:
            write(stream, frames, num_frames, exception_on_underflow)
            self._clocks[stream].write(frames)

        def stopped(stream: pyaudio.PyAudio.Stream) -> None:
            self._clocks[stream].drain()
            stop_stream(stream)

        monkeypatch.setattr(pyaudio.PyAudio, "open", opened)
        monkeypatch.setattr(pyaudio.PyAudio.Stream, "write", played)
        monkeypatch.setattr(pyaudio.PyAudio.Stream, "stop_stream", stopped)


def provide_output_device(
    device: OutputDevice,
    *,
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gives the application the output ``device`` before it starts."""
    match device:
        case OutputDevice.SILENT:
            SilentOutputDevice().install(home, monkeypatch)
        case OutputDevice.REFUSING:
            SilentOutputDevice().install(home, monkeypatch)
            _refusing_output_device(monkeypatch)
        case OutputDevice.NONE:
            _no_output_device(monkeypatch)


def _refusing_output_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """Offers the silent device and refuses every stream opened on it, as a device another program holds."""
    monkeypatch.setattr(pyaudio.PyAudio, "open", _refused_stream)


def _refused_stream(_: pyaudio.PyAudio, **__: object) -> pyaudio.PyAudio.Stream:
    raise OSError(REFUSED_STREAM)


def _no_output_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starts the application on a machine offering no output device at all."""
    monkeypatch.setattr(pyaudio.PyAudio, "get_device_count", lambda _: 0)
    monkeypatch.setattr(pyaudio.PyAudio, "get_default_output_device_info", _no_default_device)


def _no_default_device(_: pyaudio.PyAudio) -> None:
    raise OSError("A screen scenario offers no output device")
