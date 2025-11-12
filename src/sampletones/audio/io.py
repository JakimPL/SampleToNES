from pathlib import Path
from typing import Optional, Union

import numpy as np
from scipy.io import wavfile

from sampletones.constants.general import QUANTIZATION_LEVELS

from .processing import clip_audio
from .processing import normalize as normalize_audio
from .processing import quantize as quantize_audio
from .processing import read_wav_file, resample, stereo_to_mono


def write_audio(path: Union[str, Path], audio: np.ndarray, sample_rate: int) -> None:
    audio = clip_audio(audio)
    wavfile.write(path, sample_rate, audio)


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
