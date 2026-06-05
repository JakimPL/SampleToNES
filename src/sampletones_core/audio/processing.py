from typing import Tuple

import librosa
import numpy as np

from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.general import QUANTIZATION_LEVELS

from .validation import validate_audio_array


def clip_audio(audio: np.ndarray) -> np.ndarray:
    """
    Clip audio samples to the valid range [-1.0, 1.0].

    Ensures all audio samples are within the normalized range to prevent
    clipping distortion during playback or file writing.

    Args:
        audio: Audio array to clip.

    Returns:
        Clipped audio array.

    Raises:
        TypeError: If audio is not a numpy array.
    """
    validate_audio_array(audio, allowed_dims=None)
    return np.clip(audio, -1.0, 1.0)


def to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert stereo or multi-channel audio to mono by averaging channels.

    If input is already mono (1D).

    Args:
        audio: Audio array (mono or multi-channel).

    Returns:
        Mono audio array.
    """
    if audio.size == 0:
        return np.array([], dtype=audio.dtype)

    if audio.ndim == 0:
        return np.array([audio.item()], dtype=audio.dtype)

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    return audio


def resample(
    audio: np.ndarray,
    original_sample_rate: int,
    target_sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> np.ndarray:
    """
    Resample audio to a different sample rate.

    Validates input audio and performs resampling.

    Uses librosa if available for high-quality resampling, otherwise falls
    back to linear interpolation via numpy.

    Args:
        audio: Audio array to resample.
        original_sample_rate: Original sample rate in Hz.
        target_sample_rate: Target sample rate in Hz.

    Returns:
        Resampled audio array.
    """
    validate_audio_array(audio)
    if original_sample_rate == target_sample_rate:
        return audio

    return librosa.resample(audio, orig_sr=original_sample_rate, target_sr=target_sample_rate)


def interpolate(audio: np.ndarray, target_length: int) -> np.ndarray:
    """
    Interpolate audio data to a target length using linear interpolation.

    Args:
        audio: Audio array to interpolate.
        target_length: Desired length of output array.

    Returns:
        Interpolated audio array as float32.

    Raises:
        TypeError: If data is not a numpy array.
        ValueError: If data is not 1-dimensional.
    """
    if not isinstance(target_length, int):
        raise TypeError("target_length must be an integer")

    validate_audio_array(audio)
    if audio.size == 0:
        return audio.astype(np.float32)

    if target_length <= 0:
        raise ValueError("target_length must be a positive integer")

    original_length = len(audio)
    if original_length == target_length:
        return audio.astype(np.float32)

    original_indices = np.arange(original_length)
    new_indices = np.linspace(0, original_length - 1, target_length)
    interpolated_data: np.ndarray = np.interp(new_indices, original_indices, audio)
    return interpolated_data.astype(np.float32)


def minmax_decimate(audio: np.ndarray, num_buckets: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Decimate audio data using min-max downsampling for visualization.

    Divides data into buckets and extracts min and max values from each bucket,
    preserving peaks and troughs. Returns twice as many points as buckets
    (one min and one max per bucket) with corresponding x-coordinates.

    If the audio length is less than num_buckets, reduces num_buckets
    accordingly.

    Args:
        audio: Audio array to decimate.
        num_buckets: Number of buckets to divide audio into.

    Returns:
        Tuple of (x_coordinates, y_values) where each has length num_buckets * 2.

    Raises:
        TypeError: If num_buckets is not an integer or data is not a numpy array.
        ValueError: If num_buckets is not positive or data is not 1-dimensional.
    """
    if not isinstance(num_buckets, int):
        raise TypeError("num_buckets must be an integer")

    if num_buckets <= 0:
        raise ValueError("num_buckets must be a positive integer")

    validate_audio_array(audio)
    if audio.size == 0:
        return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

    length = len(audio)
    num_buckets = min(num_buckets, length)

    data = audio.astype(float)
    starts = np.arange(num_buckets) * length // num_buckets

    mins = np.minimum.reduceat(data, starts)
    maxs = np.maximum.reduceat(data, starts)

    y_values = np.empty(num_buckets * 2, dtype=float)
    y_values[0::2] = mins
    y_values[1::2] = maxs

    return np.repeat(starts.astype(float), 2), y_values


def normalize(audio: np.ndarray, nan_value: float = 0.0) -> np.ndarray:
    """
    Normalize audio to [-1.0, 1.0] range 32-bit float array,
    based on peak amplitude.

    Replaces NaN and infinity values with 0.0, then scales the audio so the
    maximum absolute value becomes 1.0. If audio has no peak (all zeros),
    returns unchanged.

    Args:
        audio: Audio array to normalize.
        nan_value: Value to replace NaN and infinity samples with.

    Returns:
        Normalized audio array.

    Raises:
        TypeError: If audio is not a numpy array.
        ValueError: If audio is not 1-dimensional.
    """
    validate_audio_array(audio)
    audio = audio.astype(np.float32)
    if audio.size == 0:
        return audio

    audio = np.nan_to_num(audio, nan=nan_value, posinf=nan_value, neginf=nan_value)
    peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
    if peak > 0.0:
        audio /= peak

    return audio


def quantize(audio: np.ndarray, levels: int = QUANTIZATION_LEVELS) -> np.ndarray:
    """
    Quantize audio to a discrete number of amplitude levels.

    Reduces audio bit depth by rounding to discrete levels, simulating
    lower bit-depth audio. Automatically adjusts even level counts to odd
    to ensure zero is included as a level.

    Args:
        audio: Audio array to quantize.
        levels: Number of quantization levels (minimum 3).

    Returns:
        Quantized audio array.

    Raises:
        TypeError: If levels is not an integer or audio is not a numpy array.
        ValueError: If levels is less than 3 or audio is not 1-dimensional.
    """
    if not isinstance(levels, int):
        raise TypeError("levels must be an integer")

    if levels < 3:
        raise ValueError("levels must be at least 3")

    validate_audio_array(audio)
    n = 2 * ((levels - 1) // 2)
    return 2.0 * np.round((audio + 1.0) / 2.0 * n) / n - 1.0
