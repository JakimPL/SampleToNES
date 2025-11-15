import warnings
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
from scipy.io import wavfile

from sampletones.constants.general import QUANTIZATION_LEVELS

from .processing import clip_audio
from .processing import normalize as normalize_audio
from .processing import quantize as quantize_audio
from .processing import resample, stereo_to_mono


def write_wave(path: Union[str, Path], sample_rate: int, audio: np.ndarray) -> None:
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


def read_wave(path: Union[str, Path]) -> Tuple[np.ndarray, int]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", wavfile.WavFileWarning)
        sample_rate, audio = wavfile.read(path)

    if audio.dtype == np.uint8:
        audio = (audio - 128) / 128.0
    elif audio.dtype == np.int16:
        audio = audio / 32768.0
    elif audio.dtype == np.int32:
        audio = audio / 2147483648.0
    elif not np.issubdtype(audio.dtype, np.floating):
        raise ValueError(f"Unsupported audio data type: {audio.dtype}")

    audio = np.asarray(audio).astype(np.float32)
    return audio, sample_rate


def load_audio(
    path: Union[str, Path],
    target_sample_rate: Optional[int] = None,
    normalize: bool = True,
    quantize: bool = True,
) -> np.ndarray:
    audio, sample_rate = read_wave(path)
    audio = stereo_to_mono(audio)

    if normalize:
        audio = normalize_audio(audio)

    target_sample_rate = target_sample_rate or sample_rate
    audio = resample(audio, original_sample_rate=sample_rate, target_sample_rate=target_sample_rate)

    if quantize:
        audio = quantize_audio(audio, levels=QUANTIZATION_LEVELS)

    return audio
