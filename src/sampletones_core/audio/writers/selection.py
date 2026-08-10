from pathlib import Path
from typing import Mapping, Tuple

import soundfile

from sampletones_shared.exceptions import UnsupportedAudioFormatError

from .capability import capability_of
from .format import AudioDepth, AudioFormat
from .protocol import AudioWriter
from .soundfile import CONTAINERS, FIXED_SUBTYPES, SUBTYPES, SoundFileAudioWriter
from .spec import AudioOutputSpec


def available_audio_formats() -> Tuple[AudioFormat, ...]:
    """The formats this installation writes, in the order a chooser offers them.

    libsndfile is built with a codec set that varies by platform and packaging, and the MP3 encoder
    in particular is present only where it was compiled in. Asking the library what it holds keeps
    a chooser honest about the machine it is running on.

    Returns:
        Tuple[AudioFormat, ...]: The formats that can be written here.
    """
    containers = soundfile.available_formats()
    return tuple(audio_format for audio_format in AudioFormat if _is_writable(audio_format, containers))


def available_depths(audio_format: AudioFormat) -> Tuple[AudioDepth, ...]:
    """The depths this installation stores ``audio_format`` samples at, coarsest first.

    Args:
        audio_format: The container to describe.

    Returns:
        Tuple[AudioDepth, ...]: The depths the format declares that the encoder also writes; empty
            for a format that sets its own and offers a bitrate instead.
    """
    container = CONTAINERS[audio_format]
    return tuple(
        depth
        for depth in capability_of(audio_format).depths
        if soundfile.check_format(
            container,
            SUBTYPES[depth],
        )
    )


def open_audio_writer(path: Path, spec: AudioOutputSpec) -> AudioWriter:
    """Opens a writer for ``path`` in the format ``spec`` states.

    The writer is a context manager: entering it opens the file and leaving it finalizes what was
    written.

    Args:
        path: Where the file is written.
        spec: The format, rate, and quality it is written at.

    Returns:
        AudioWriter: A writer ready to be entered.

    Raises:
        UnsupportedAudioFormatError: If this installation does not write the requested format.
    """
    if spec.audio_format not in available_audio_formats():
        raise UnsupportedAudioFormatError(f"This installation does not write {spec.audio_format} files")

    return SoundFileAudioWriter(path, spec)


def _is_writable(audio_format: AudioFormat, containers: Mapping[str, str]) -> bool:
    container = CONTAINERS[audio_format]
    if container not in containers:
        return False

    if capability_of(audio_format).stores_samples:
        return bool(available_depths(audio_format))

    return bool(soundfile.check_format(container, FIXED_SUBTYPES[audio_format]))
