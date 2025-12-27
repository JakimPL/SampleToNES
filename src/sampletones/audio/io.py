from typing import Optional, Tuple

import numpy as np
from scipy.io import wavfile
from soundfile import read as sf_read

from sampletones.constants.general import QUANTIZATION_LEVELS
from sampletones.typehints import Pathlike

from .processing import clip_audio
from .processing import normalize as normalize_audio
from .processing import quantize as quantize_audio
from .processing import resample, stereo_to_mono


def write_wave(path: Pathlike, sample_rate: int, audio: np.ndarray) -> None:
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


def read_wave(path: Pathlike) -> Tuple[np.ndarray, int]:
    audio, sample_rate = sf_read(path, dtype="float32")
    return audio, sample_rate


def load_audio(
    path: Pathlike,
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
