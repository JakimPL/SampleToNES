import pyaudio


class PyAudioOutputStream:
    """A PortAudio stream reached through PyAudio, written in blocking mode.

    Each call reaches the PyAudio stream's own method at the moment it is made, so a stand-in installed
    on PyAudio's stream class answers it.
    """

    def __init__(self, stream: pyaudio.Stream) -> None:
        self._stream = stream

    def write(self, data: bytes) -> None:
        self._stream.write(data)

    def drain(self) -> None:
        self._stream.stop_stream()

    def close(self) -> None:
        self._stream.close()
