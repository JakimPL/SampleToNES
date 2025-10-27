from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
from IPython.display import Audio, display
from scipy.io import wavfile

from constants import QUANTIZATION_LEVELS, SAMPLE_RATE


def clip_audio(audio: np.ndarray) -> np.ndarray:
    return np.clip(audio, -1.0, 1.0)


def play_audio(audio: np.ndarray, sample_rate: int) -> None:
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


def write_audio(path: Union[str, Path], audio: np.ndarray, sample_rate: int) -> None:
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


def stereo_to_mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    return audio


def resample(audio: np.ndarray, original_sample_rate: int, target_sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    if original_sample_rate == target_sample_rate:
        return audio

    try:
        import librosa

        audio = librosa.resample(audio, orig_sr=original_sample_rate, target_sr=target_sample_rate)
        return audio
    except ImportError:
        pass

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
    interpolated_data = np.interp(new_indices, original_indices, data)

    return interpolated_data.astype(np.float32)


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
    target_sample_rate: Optional[int] = None,
    normalize: bool = True,
    quantize: bool = True,
) -> np.ndarray:
    audio, sample_rate = read_wav_file(path)
    audio = stereo_to_mono(audio)

    if normalize:
        audio = normalize_audio(audio)

    target_sample_rate = target_sample_rate or sample_rate
    audio = resample(audio, original_sample_rate=sample_rate, target_sample_rate=target_sample_rate)

    if quantize:
        audio = quantize_audio(audio, levels=QUANTIZATION_LEVELS)

    return audio
