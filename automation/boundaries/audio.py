import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, List, Optional, Tuple
from weakref import WeakKeyDictionary

import numpy as np
import pyaudio
import pytest

ALSA_CONFIGURATION_FILE: Final[str] = ".asound.conf"
ALSA_CONFIGURATION_VARIABLE: Final[str] = "ALSA_CONFIG_PATH"
DEVICE_BUFFER_SECONDS: Final[float] = 0.05
SILENT_DEFAULT_DEVICE: Final[str] = "pcm.!default {\n    type null\n}\n"
SILENT_DEVICE_NAME: Final[str] = "default"
REFUSED_STREAM: Final[str] = "A screen scenario's device refuses every stream"
JACK_SERVER_VARIABLE: Final[str] = "JACK_DEFAULT_SERVER"
JACK_NO_START_VARIABLE: Final[str] = "JACK_NO_START_SERVER"
ABSENT_JACK_SERVER: Final[str] = "sampletones-screens-absent"
JACK_STAYS_DOWN: Final[str] = "1"


class OutputDevice(StrEnum):
    """The output a scenario's machine offers: a device that plays into silence, one that refuses every
    stream, or none at all."""

    SILENT = "silent"
    REFUSING = "refusing"
    NONE = "none"


@dataclass(frozen=True)
class StreamReading:
    """One output stream the application opened, as the device met it.

    Attributes:
        rate: The samples a second the stream played.
        frames: The frames written to it.
        closed: Whether the application closed it.
    """

    rate: int
    frames: int
    closed: bool


@dataclass
class _StreamLog:
    """What the device met of one stream so far."""

    rate: int
    bytes_per_frame: int
    frames: int = 0
    closed: bool = False

    def reading(self) -> StreamReading:
        return StreamReading(rate=self.rate, frames=self.frames, closed=self.closed)


class OutputRecord:
    """What the application did with its output device: the streams it opened, what it wrote to each, how many
    of the samples it played carry sound, and how often it terminated the backend.

    It wraps the calls every output stream and every backend instance takes, so a sound counts once it reaches
    the device, however briefly it plays and however many frames pass between two readings of it. The
    playback thread writes while a scenario reads, so the record stands behind a lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sounding_samples = 0
        self._streams: List[_StreamLog] = []
        self._logs: WeakKeyDictionary[pyaudio.PyAudio.Stream, _StreamLog] = WeakKeyDictionary()
        self._terminations = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Puts the record in front of the backend's open and terminate, and of every stream's write and close,
        before the application starts.

        ``PyAudio.open`` builds its streams from ``PyAudio.Stream``, the class whose calls are wrapped.
        """
        open_stream = pyaudio.PyAudio.open
        terminate = pyaudio.PyAudio.terminate
        write = pyaudio.PyAudio.Stream.write
        close = pyaudio.PyAudio.Stream.close

        def opened(
            audio: pyaudio.PyAudio,
            *,
            rate: int,
            channels: int,
            format: int,  # pylint: disable=redefined-builtin
            **options: object,
        ) -> pyaudio.PyAudio.Stream:
            stream = open_stream(audio, rate=rate, channels=channels, format=format, **options)
            self._opened(
                stream,
                _StreamLog(
                    rate=rate,
                    bytes_per_frame=channels * pyaudio.get_sample_size(format),
                ),
            )
            return stream

        def recorded(
            stream: pyaudio.PyAudio.Stream,
            frames: bytes,
            num_frames: Optional[int] = None,
            exception_on_underflow: bool = False,
        ) -> None:
            self._count(stream, frames)
            write(stream, frames, num_frames, exception_on_underflow)

        def closed(stream: pyaudio.PyAudio.Stream) -> None:
            close(stream)
            self._closed(stream)

        def terminated(audio: pyaudio.PyAudio) -> None:
            terminate(audio)
            with self._lock:
                self._terminations += 1

        monkeypatch.setattr(pyaudio.PyAudio, "open", opened)
        monkeypatch.setattr(pyaudio.PyAudio, "terminate", terminated)
        monkeypatch.setattr(pyaudio.PyAudio.Stream, "write", recorded)
        monkeypatch.setattr(pyaudio.PyAudio.Stream, "close", closed)

    def sounding_samples(self) -> int:
        """How many samples carrying sound the application has written to its output so far."""
        with self._lock:
            return self._sounding_samples

    def streams(self) -> Tuple[StreamReading, ...]:
        """Every output stream the application opened so far, in the order it opened them."""
        with self._lock:
            return tuple(log.reading() for log in self._streams)

    def terminations(self) -> int:
        """How many backend instances the application terminated so far."""
        with self._lock:
            return self._terminations

    def _opened(self, stream: pyaudio.PyAudio.Stream, log: _StreamLog) -> None:
        with self._lock:
            self._streams.append(log)
            self._logs[stream] = log

    def _count(self, stream: pyaudio.PyAudio.Stream, frames: bytes) -> None:
        sounding = int(np.count_nonzero(np.frombuffer(frames, dtype=np.float32)))
        with self._lock:
            self._sounding_samples += sounding
            log = self._logs.get(stream)
            if log is not None:
                log.frames += len(frames) // log.bytes_per_frame

    def _closed(self, stream: pyaudio.PyAudio.Stream) -> None:
        with self._lock:
            log = self._logs.get(stream)
            if log is not None:
                log.closed = True


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
    """The one output device a scenario's application finds: ALSA's null sink, played out in real time, which
    PortAudio names :data:`SILENT_DEVICE_NAME`.

    The scenario's ALSA reads a configuration of its own, which names the null sink its default device and
    leaves the machine's sound cards and sound server out, so every machine offers the same device and plays
    into silence. The null sink takes sound as fast as it comes, so a clock behind each output stream returns
    a write and a stop when a device would.
    """

    def __init__(self) -> None:
        self._clocks: WeakKeyDictionary[pyaudio.PyAudio.Stream, DeviceClock] = WeakKeyDictionary()

    @staticmethod
    def configure(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Points the scenario's ALSA at a configuration of its own, whose one device is the null sink."""
        configuration = home / ALSA_CONFIGURATION_FILE
        configuration.write_text(SILENT_DEFAULT_DEVICE, encoding="utf-8")
        monkeypatch.setenv(ALSA_CONFIGURATION_VARIABLE, str(configuration))

    def keep_time(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Puts a clock behind every stream before the application starts, so the null sink plays in real time."""
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
    """Gives the application the output ``device`` before it starts, with the machine's own sound kept out.

    Whatever the device, the scenario's ALSA reads its own configuration and JACK looks for a server no
    one runs, so neither the sound cards nor a sound server running on the machine reach the run.
    """
    silent = SilentOutputDevice()
    silent.configure(home, monkeypatch)
    _away_from_jack(monkeypatch)
    match device:
        case OutputDevice.SILENT:
            silent.keep_time(monkeypatch)
        case OutputDevice.REFUSING:
            silent.keep_time(monkeypatch)
            _refusing_output_device(monkeypatch)
        case OutputDevice.NONE:
            _no_output_device(monkeypatch)


def _away_from_jack(monkeypatch: pytest.MonkeyPatch) -> None:
    """Points JACK at a server no one runs, and keeps it from starting one."""
    monkeypatch.setenv(JACK_SERVER_VARIABLE, ABSENT_JACK_SERVER)
    monkeypatch.setenv(JACK_NO_START_VARIABLE, JACK_STAYS_DOWN)


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
