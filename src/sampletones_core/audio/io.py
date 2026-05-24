from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy.io import wavfile
from soundfile import read as sf_read

from sampletones_core.constants.general import QUANTIZATION_LEVELS
from sampletones_shared.types.path import Pathlike

from .processing import clip_audio
from .processing import normalize as normalize_audio
from .processing import quantize as quantize_audio
from .processing import resample, to_mono
from .validation import validate_audio_array, validate_sample_rate


def write_wave(path: Pathlike, sample_rate: int, audio: np.ndarray) -> None:
    """
    Write audio data to a WAV file with specified sample rate.

    Audio is automatically clipped to [-1.0, 1.0] range before writing.

    Args:
        path: File path where WAV file will be written.
        sample_rate: Sample rate in Hz (must be one of the allowed rates).
        audio: Audio array to write (can be mono or stereo).

    Raises:
        TypeError: If sample_rate is not an integer or audio is not a numpy array.
        ValueError: If sample_rate is not in allowed sample rates or audio has invalid dimensions.
    """
    validate_sample_rate(sample_rate)
    validate_audio_array(audio, allowed_dims=(1, 2))
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


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


def load_audio(
    path: Pathlike,
    *,
    target_sample_rate: Optional[int] = None,
    normalize: bool = True,
    quantize: bool = True,
) -> np.ndarray:
    """
    Load audio from file with optional processing (mono conversion, normalization, resampling, quantization).

    Processing pipeline:
    1. Read audio file.
    2. Convert to mono.
    3. Normalize to [-1.0, 1.0] (if enabled).
    4. Resample to target sample rate (if specified).
    5. Quantize to discrete levels (if enabled).

    Args:
        path: Path to the audio file to load.
        target_sample_rate: Target sample rate in Hz. If None, uses original sample rate.
        normalize: Whether to normalize audio to peak amplitude of 1.0.
        quantize: Whether to quantize audio to discrete levels.

    Returns:
        Processed mono audio array as float32.

    Raises:
        TypeError: If target_sample_rate is not an integer.
        ValueError: If target_sample_rate is not in allowed sample rates.
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory instead of a file.
        RuntimeError: If the file format is invalid or corrupted.
    """
    if target_sample_rate is not None:
        validate_sample_rate(target_sample_rate)

    audio, sample_rate = read_wave(path)
    audio = to_mono(audio)

    if normalize:
        audio = normalize_audio(audio)

    target_sample_rate = target_sample_rate or sample_rate
    audio = resample(audio, original_sample_rate=sample_rate, target_sample_rate=target_sample_rate)

    if quantize:
        audio = quantize_audio(audio, levels=QUANTIZATION_LEVELS)

    return audio
