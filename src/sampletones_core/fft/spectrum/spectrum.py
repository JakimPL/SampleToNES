from typing import Optional, Union

import numpy as np

from sampletones_core.constants.spectrum import BINS_PER_OCTAVE
from sampletones_core.structures.histogram import Histogram

from .cqt import calculate_cqt_spectrum
from .fft import calculate_fft_spectrum, calculate_log_spaced_fft_spectrum
from .method import SpectrumMethod


def calculate_spectrum(
    method: Union[str, SpectrumMethod],
    audio: np.ndarray,
    sample_rate: int,
    fft_size: Optional[int] = None,
    bins_per_octave: int = BINS_PER_OCTAVE,
    n_bins: Optional[int] = None,
) -> Histogram:
    """
    Compute the spectrum of the given audio data, for given FFT size and sample rate,
    depending on the selected spectrum calculation method. Each method starts its axis at its
    own floor: the constant-Q transform at the triangle's lowest note, and the log-spaced FFT at
    the lowest frequency its window spans two cycles of.

    Args:
        method: Spectrum calculation method.
        audio: Input audio data.
        sample_rate: Sample rate of the audio data.
        fft_size: Size of the FFT to be used. If None, uses the length of the audio array.
        bins_per_octave: Number of bins per octave. Only used if n_bins is None.
        n_bins: Number of constant-Q components. Only used by the constant-Q method.

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
                bins_per_octave=bins_per_octave,
            )
        case SpectrumMethod.CQT:
            spectrum = calculate_cqt_spectrum(
                audio,
                sample_rate,
                bins_per_octave=bins_per_octave,
                n_bins=n_bins,
            )
        case _:
            raise ValueError(f"Unsupported spectrum method: {method}")

    return spectrum
