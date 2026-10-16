from typing import Optional

import pyaudio

from sampletones_shared.utils.system.locales import to_utf8

from ..device import DriverDevice
from .constants import CHANNELS, FORMAT
from .stderr import captured_stderr
from .stream import PyAudioOutputStream


class PyAudioDriver:
    """The audio backend through PyAudio, which wraps PortAudio.

    PortAudio's quirks, each answered here:

    - ALSA prints configuration notes on standard error as PortAudio starts and stops, so both run
      with standard error routed to the log.
    - PyAudio reports device names in the system's preferred encoding, so each name is read as UTF-8.
    - PyAudio answers a format a device refuses with ``ValueError``, which reads as an unsupported rate.
    - PyAudio raises ``OSError`` where the system names no default output device, which reads as none.
    - ``Pa_StopStream`` plays out what the device holds, and ``Pa_CloseStream`` on an active stream
      discards it, which is the drain and the close of a stream.

    Each call reaches the PyAudio instance's own method at the moment it is made, so a stand-in installed
    on PyAudio's class answers it.
    """

    def __init__(self) -> None:
        with captured_stderr():
            self._pyaudio = pyaudio.PyAudio()

    def device_count(self) -> int:
        return int(self._pyaudio.get_device_count())

    def device(self, index: int) -> DriverDevice:
        info = self._pyaudio.get_device_info_by_index(index)
        return DriverDevice(
            index=index,
            name=to_utf8(str(info["name"])),
            max_output_channels=int(info["maxOutputChannels"]),
            default_sample_rate=int(info["defaultSampleRate"]),
            host_api=int(info["hostApi"]),
        )

    def default_output_index(self) -> Optional[int]:
        try:
            info = self._pyaudio.get_default_output_device_info()
        except OSError:
            return None

        return int(info["index"])

    def supports(self, index: int, sample_rate: int) -> bool:
        try:
            self._pyaudio.is_format_supported(
                rate=sample_rate,
                output_device=index,
                output_channels=CHANNELS,
                output_format=FORMAT,
            )
        except ValueError:
            return False

        return True

    def open_output(
        self,
        *,
        device_index: int,
        sample_rate: int,
        frames_per_buffer: Optional[int],
    ) -> PyAudioOutputStream:
        stream = self._pyaudio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=sample_rate,
            output=True,
            output_device_index=device_index,
            frames_per_buffer=(
                pyaudio.paFramesPerBufferUnspecified if frames_per_buffer is None else frames_per_buffer
            ),
        )
        return PyAudioOutputStream(stream)

    def terminate(self) -> None:
        with captured_stderr():
            self._pyaudio.terminate()
