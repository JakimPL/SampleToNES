from typing import Optional, Union

import numpy as np

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.structures.histogram import Histogram

from .cqt import calculate_cqt_spectrum
from .fft import calculate_fft_spectrum, calculate_log_spaced_fft_spectrum
from .method import SpectrumMethod


def calculate_spectrum(
    method: Union[str, SpectrumMethod],
    audio: np.ndarray,
    sample_rate: int,
    fft_size: Optional[int] = None,
    cutoff: float = CQT_CUTOFF_FREQUENCY,
    bins_per_octave: int = BINS_PER_OCTAVE,
    n_bins: Optional[int] = None,
) -> Histogram:
    """
    Compute the spectrum of the given audio data, for given FFT size and sample rate,
    depending on the selected spectrum calculation method.

    Args:
        method: Spectrum calculation method.
        audio: Input audio data.
        sample_rate: Sample rate of the audio data.
        fft_size: Size of the FFT to be used. If None, uses the length of the audio array.
        cutoff: Cutoff frequency. All frequencies below this value will be discarded.
        bins_per_octave: Number of bins per octave. Only used if n_bins is None.
        n_bins: Number of logarithmically spaced components.

    Returns:
        Histogram: Computed spectrum.

    Raises:
        ValueError: If an unsupported spectrum method is provided.
    """
    method = SpectrumMethod(method)
    spectrum: Histogram
    match method:
        case SpectrumMethod.FFT:
            spectrum = calculate_fft_spectrum(
                audio,
                sample_rate,
                fft_size,
            )
        case SpectrumMethod.LOG_SPACED_FFT:
            spectrum = calculate_log_spaced_fft_spectrum(
                audio,
                sample_rate,
                fft_size,
                cutoff,
                bins_per_octave,
                n_bins,
            )
        case SpectrumMethod.CQT:
            spectrum = calculate_cqt_spectrum(
                audio,
                sample_rate,
                cutoff,
                bins_per_octave,
                n_bins,
            )
        case _:
            raise ValueError(f"Unsupported spectrum method: {method}")

    return spectrum
