from pathlib import Path
from typing import Tuple, Union

import numpy as np
from IPython.display import Audio, display
from scipy.io import wavfile

from constants import QUANTIZATION_LEVELS, SAMPLE_RATE

try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


def clip_audio(audio: np.ndarray) -> np.ndarray:
    return np.clip(audio, -1.0, 1.0)


def play_audio(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    audio = clip_audio(audio)
    display(Audio(data=audio, rate=sample_rate))


def read_wav_file(path: Union[str, Path]) -> Tuple[np.ndarray, int]:
    sample_rate, audio = wavfile.read(path)
    audio = np.asarray(audio).astype(np.float32)
    if audio.dtype == np.int16:
        audio = audio / 32768.0
    elif audio.dtype == np.int32:
        audio = audio / 2147483648.0
    elif audio.dtype == np.uint8:
        audio = (audio - 128.0) / 128.0

    return audio, sample_rate


def write_audio(path: Union[str, Path], audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


def stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    return audio


def resample(audio: np.ndarray, original_sample_rate: int, target_sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    if original_sample_rate == target_sample_rate:
        return audio

    if LIBROSA_AVAILABLE:
        audio = librosa.resample(audio, orig_sr=original_sample_rate, target_sr=target_sample_rate)
        return audio

    ratio = target_sample_rate / original_sample_rate

    original_length = len(audio)
    new_length = int(original_length * ratio)

    original_indices = np.arange(original_length)
    new_indices = np.linspace(0, original_length - 1, new_length)
    resampled_audio = np.interp(new_indices, original_indices, audio)

    return resampled_audio.astype(np.float32)


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    peak = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
    if peak > 0.0:
        audio /= peak
    return audio


def quantize_audio(audio: np.ndarray, levels: int = QUANTIZATION_LEVELS) -> np.ndarray:
    n = levels // 2
    audio = np.round(audio * (n - 1)) / (n - 1)
    return audio


def load_audio(
    path: Union[str, Path],
    target_sample_rate: int = SAMPLE_RATE,
    normalize: bool = True,
    quantize: bool = True,
) -> np.ndarray:
    audio, sample_rate = read_wav_file(path)
    audio = stereo_to_mono(audio)

    if normalize:
        audio = normalize_audio(audio)

    audio = resample(audio, original_sample_rate=sample_rate, target_sample_rate=target_sample_rate)

    if quantize:
        audio = quantize_audio(audio, levels=QUANTIZATION_LEVELS)

    return audio
