from pathlib import Path
from types import TracebackType
from typing import Any, Dict, Final, Mapping, Optional, Self, Type

import numpy as np
import soundfile

from sampletones_shared.exceptions import AudioWriteError

from .bitrate import mp3_compression_level
from .format import AudioDepth, AudioFormat
from .spec import AudioOutputSpec, Mp3OutputSpec, WaveOutputSpec

CONTAINERS: Final[Mapping[AudioFormat, str]] = {
    AudioFormat.WAVE: "WAV",
    AudioFormat.MP3: "MP3",
}

SUBTYPES: Final[Mapping[AudioDepth, str]] = {
    AudioDepth.PCM_U8: "PCM_U8",
    AudioDepth.PCM_16: "PCM_16",
    AudioDepth.PCM_24: "PCM_24",
    AudioDepth.PCM_32: "PCM_32",
    AudioDepth.FLOAT_32: "FLOAT",
}

MP3_SUBTYPE: Final[str] = "MPEG_LAYER_III"

FIXED_SUBTYPES: Final[Mapping[AudioFormat, str]] = {
    AudioFormat.MP3: MP3_SUBTYPE,
}

CONSTANT_BITRATE_MODE: Final[str] = "CONSTANT"
WRITE_MODE: Final[str] = "w"
CHANNELS: Final[int] = 1


def encoding_arguments(spec: AudioOutputSpec) -> Dict[str, Any]:
    """The libsndfile settings that write ``spec``.

    This is where the encoder's vocabulary is spoken: eight-bit WAV is unsigned where the deeper
    integer forms are signed, the float form is named for its width alone, and MP3 takes its
    quality as a compression level rather than a bitrate.

    Args:
        spec: The format, rate, and quality the file is written at.

    Returns:
        Dict[str, Any]: Keyword arguments for opening a ``soundfile.SoundFile`` for writing.
    """
    match spec:
        case WaveOutputSpec(depth=depth):
            return {
                "format": CONTAINERS[AudioFormat.WAVE],
                "subtype": SUBTYPES[depth],
            }
        case Mp3OutputSpec(sample_rate=sample_rate, bitrate=bitrate):
            return {
                "format": CONTAINERS[AudioFormat.MP3],
                "subtype": MP3_SUBTYPE,
                "bitrate_mode": CONSTANT_BITRATE_MODE,
                "compression_level": mp3_compression_level(sample_rate, bitrate),
            }


class SoundFileAudioWriter:
    """Writes rendered audio to a file through libsndfile.

    Holds the file open for the length of a ``with`` block and appends each chunk as it arrives,
    so a render streams to disk while it is being produced.

    Attributes:
        path: Where the file is written.
        spec: The format, rate, and quality it is written at.
    """

    def __init__(self, path: Path, spec: AudioOutputSpec) -> None:
        self.path = path
        self.spec = spec
        self._file: Optional[soundfile.SoundFile] = None

    def __enter__(self) -> Self:
        self._file = soundfile.SoundFile(
            self.path,
            mode=WRITE_MODE,
            samplerate=self.spec.sample_rate,
            channels=CHANNELS,
            **encoding_arguments(self.spec),
        )
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        opened, self._file = self._file, None
        if opened is not None:
            opened.close()

    def write(self, chunk: np.ndarray) -> None:
        """Appends one chunk of mono float32 audio to the file.

        Args:
            chunk: The samples to append, in the range [-1, 1]. Values outside it are held at the
                range's edge by the integer depths and kept as they stand by the float depth.

        Raises:
            AudioWriteError: If the file is not open, which is to say the call is outside the
                ``with`` block that owns it.
        """
        if self._file is None:
            raise AudioWriteError(f"No file open at '{self.path}'; write within the writer's context")

        self._file.write(chunk)
