from pathlib import Path
from typing import Final, Sequence, Tuple

import numpy as np
from scipy.io import wavfile
from soundfile import SoundFileError
from soundfile import read as sf_read
from soundfile import write as sf_write

from sampletones_shared.exceptions import AudioReadError
from sampletones_shared.types.path import Pathlike

from .mixing import align, common_length, mix
from .processing import clip_audio
from .processing import quantize as quantize_audio
from .processing import resample, to_mono
from .validation import validate_audio_array, validate_sample_rate

FLAC_FORMAT: Final[str] = "FLAC"
FLAC_SUBTYPE: Final[str] = "PCM_16"
UNIT_SCALE: Final[float] = 1.0


def write_wave(path: Pathlike, sample_rate: int, audio: np.ndarray) -> None:
    """
    Write audio data to a WAV file with specified sample rate.

    Audio is automatically clipped to [-1.0, 1.0] range before writing.

    Args:
        path: File path where WAV file will be written.
        sample_rate: Sample rate in Hz, within ``MIN_SAMPLE_RATE..MAX_SAMPLE_RATE``.
        audio: Audio array to write (can be mono or stereo).

    Raises:
        TypeError: If sample_rate is not an integer or audio is not a numpy array.
        ValueError: If sample_rate lies outside the accepted range or audio has invalid dimensions.
    """
    validate_sample_rate(sample_rate)
    validate_audio_array(audio, allowed_dims=(1, 2))
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


def write_flac(path: Pathlike, sample_rate: int, audio: np.ndarray) -> None:
    """
    Write audio data to a FLAC file with specified sample rate.

    The samples are clipped to the valid wave range and stored as 16-bit integers, a lossless
    encoding every audio player and every browser reads, at about a third of the size the same
    audio takes as 32-bit floating point.

    Args:
        path: File path where the FLAC file will be written.
        sample_rate: Sample rate in Hz, within ``MIN_SAMPLE_RATE..MAX_SAMPLE_RATE``.
        audio: Audio array to write (can be mono or stereo).

    Raises:
        TypeError: If sample_rate is not an integer or audio is not a numpy array.
        ValueError: If sample_rate lies outside the accepted range or audio has invalid dimensions.
    """
    validate_sample_rate(sample_rate)
    validate_audio_array(audio, allowed_dims=(1, 2))
    sf_write(
        path,
        clip_audio(audio),
        sample_rate,
        subtype=FLAC_SUBTYPE,
        format=FLAC_FORMAT,
    )


def read_wave(path: Pathlike) -> Tuple[np.ndarray, int]:
    """
    Read audio data and sample rate from an audio file.

    Audio is returned as float32 array. Can handle both mono and stereo files.

    Args:
        path: Path to the audio file to read.

    Returns:
        Tuple of (audio_array, sample_rate) where audio_array is float32.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory instead of a file.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File '{path}' does not exist")

    if not path.is_file():
        raise IsADirectoryError(f"Path '{path}' is not a file")

    audio, sample_rate = sf_read(path, dtype="float32")
    return audio, sample_rate


def read_mono(path: Pathlike) -> Tuple[np.ndarray, int]:
    """Reads an audio file as one channel at the rate it was recorded at, the form a preview sounds.

    Returns:
        Tuple of (audio_array, sample_rate) where audio_array is mono float32.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory instead of a file.
        AudioReadError: If the file holds no audio the reader understands.
    """
    try:
        audio, sample_rate = read_wave(path)
    except SoundFileError as error:
        raise AudioReadError(f"Failed to read audio file '{path}': {error}") from error

    return to_mono(audio), sample_rate


def read_recording(path: Pathlike, *, target_sample_rate: int) -> np.ndarray:
    """
    Read a recording as one mono channel at ``target_sample_rate``, at the level captured.

    Scaling a recording belongs to the set it is read in, so every reader that brings recordings to
    a working level reads them here and scales the whole set afterwards, as :func:`mix_scale`
    and :func:`scale_stems` do.

    Args:
        path: Path to the audio file to read.
        target_sample_rate: Sample rate in Hz the recording is resampled to.

    Returns:
        The mono recording as float32.

    Raises:
        TypeError: If target_sample_rate is not an integer.
        ValueError: If target_sample_rate lies outside the accepted range.
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory instead of a file.
        RuntimeError: If the file format is invalid or corrupted.
    """
    validate_sample_rate(target_sample_rate)
    audio, sample_rate = read_wave(path)
    return resample(to_mono(audio), original_sample_rate=sample_rate, target_sample_rate=target_sample_rate)


def read_stems(
    paths: Sequence[Pathlike],
    *,
    target_sample_rate: int,
) -> Tuple[np.ndarray, ...]:
    """
    Read a set of recordings onto one sample rate and one shared length, at the levels captured.

    Each recording is mixed to mono and resampled, a shorter one runs on in silence to the length
    of the longest, and a sample the file states no finite value for reads as silence. The levels
    stay as the files hold them, so the balance they were captured in is what a scale then keeps.

    Args:
        paths: Paths to the recordings, in the order they are returned.
        target_sample_rate: Sample rate every recording is resampled to.

    Returns:
        The recordings in the order given, each one the length of the longest.

    Raises:
        ValueError: If ``target_sample_rate`` lies outside the accepted range.
        FileNotFoundError: If a path names no file.
        IsADirectoryError: If a path points at a directory.
    """
    recordings = [read_recording(path, target_sample_rate=target_sample_rate) for path in paths]
    aligned = align(recordings, common_length(recordings))
    return tuple(np.nan_to_num(recording, nan=0.0, posinf=0.0, neginf=0.0) for recording in aligned)


def mix_scale(recordings: Sequence[np.ndarray], *, normalize: bool) -> float:
    """
    The factor a set of recordings is divided by to bring the peak of their mix to full range.

    The recordings of one piece stand in the balance the piece was mixed at, so the whole set is
    scaled by the one factor drawn from the peak of their sum. Each recording then keeps the level
    it holds in the mix, which is what lets one of them be heard on its own at the level it sounds
    there. Scaling one recording by the peak of its own sum is normalizing it.

    Args:
        recordings: The recordings of one set, sharing a length.
        normalize: Whether the set is brought to full range at all.

    Returns:
        float: The peak of the mix, and ``UNIT_SCALE`` where normalization is off or the set is
            silent throughout.
    """
    if not normalize or not recordings:
        return UNIT_SCALE

    peak = float(np.max(np.abs(mix(list(recordings)))))
    return peak if peak > 0.0 else UNIT_SCALE


def scale_stems(
    recordings: Sequence[np.ndarray],
    *,
    scale: float,
    quantize: bool,
    quantization_levels: int,
) -> Tuple[np.ndarray, ...]:
    """
    Bring every recording of a set to the level ``scale`` sets for it.

    Each recording is divided by the one factor, so the set keeps its balance. Quantization follows
    the scaling, the order it is defined against.

    Args:
        recordings: The recordings of one set.
        scale: The factor every recording is divided by.
        quantize: Whether each scaled recording is quantized.
        quantization_levels: Number of amplitude levels used when quantization is enabled.

    Returns:
        The scaled recordings, in the order given.
    """
    scaled = [(recording / scale).astype(np.float32) for recording in recordings]
    if quantize:
        return tuple(quantize_audio(recording, levels=quantization_levels) for recording in scaled)

    return tuple(scaled)
