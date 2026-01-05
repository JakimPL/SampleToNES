from typing import Tuple

import numpy as np

from sampletones.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones.constants.general import QUANTIZATION_LEVELS
from sampletones.utils.logger import logger


def clip_audio(audio: np.ndarray) -> np.ndarray:
    return np.clip(audio, -1.0, 1.0)


def stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    return audio


def resample(
    audio: np.ndarray,
    original_sample_rate: int,
    target_sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> np.ndarray:
    if original_sample_rate == target_sample_rate:
        return audio

    try:
        import librosa

        audio = librosa.resample(audio, orig_sr=original_sample_rate, target_sr=target_sample_rate)
        return audio
    except ImportError:
        logger.debug("librosa not available, falling back to scipy interpolation")

    ratio = target_sample_rate / original_sample_rate
    original_length = len(audio)
    new_length = round(original_length * ratio)
    return interpolate(audio, target_length=new_length)


def interpolate(data: np.ndarray, target_length: int) -> np.ndarray:
    original_length = len(data)

    if original_length == target_length:
        return data.astype(np.float32)

    original_indices = np.arange(original_length)
    new_indices = np.linspace(0, original_length - 1, target_length)
    interpolated_data: np.ndarray = np.interp(new_indices, original_indices, data)

    return interpolated_data.astype(np.float32)


def minmax_decimate(data: np.ndarray, num_buckets: int) -> Tuple[np.ndarray, np.ndarray]:
    length = len(data)
    bucket_size = length / num_buckets

    x_data = np.empty(num_buckets * 2, dtype=np.float32)
    y_data = np.empty(num_buckets * 2, dtype=np.float32)

    for i in range(num_buckets):
        start = int(i * bucket_size)
        end = int((i + 1) * bucket_size)
        bucket = data[start:end]

        x_pos = (start + end) / 2
        x_data[i * 2] = x_pos
        x_data[i * 2 + 1] = x_pos
        y_data[i * 2] = bucket.min()
        y_data[i * 2 + 1] = bucket.max()

    return x_data, y_data


def normalize(audio: np.ndarray) -> np.ndarray:
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
    if peak > 0.0:
        audio /= peak
    return audio


def quantize(audio: np.ndarray, levels: int = QUANTIZATION_LEVELS) -> np.ndarray:
    n = levels // 2
    audio = np.round(audio * (n - 1)) / (n - 1)
    return audio
