import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft import FFTTransformer, Window, calculate_weights_from_edges
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.cqt.geometry import resolvable_bins
from sampletones_shared.array import xp


def calculate_spectral_weights(
    config: Config,
    window: Window,
    signal_length: int,
) -> xp.ndarray:
    """
    Per-bin weights of the spectral loss for one configuration.

    Combines the log-frequency density and the perceptual curve from
    `calculate_weights_from_edges` on the configured spectrum method's frequency
    axis, renormalizes the weights to a mean of one, and zeroes constant-Q bins the
    target signal is too short to resolve. The weighting policy of the criterion
    lives entirely in this module, so a change of perceptual model touches one place.

    Args:
        config: Configuration selecting the spectrum method and the perceptual exponent.
        window: Analysis window of the configuration.
        signal_length: Number of samples of the matching target signal.

    Returns:
        A weight per spectral bin, on the active array backend.
    """
    metric = config.generation.metric
    edges = _reference_edges(config, window)
    weights = xp.asarray(calculate_weights_from_edges(edges, metric.perceptual_exponent))
    weights = len(weights) * weights / xp.sum(weights)
    return weights * _reliability_mask(config, signal_length, int(weights.shape[-1]))


def _reference_edges(config: Config, window: Window) -> np.ndarray:
    """
    Frequency-bin edges of the configured feature axis.

    The edges are read off the feature of a zero signal, so they match exactly the
    axis every target and candidate feature is computed on.
    """
    transformer = FFTTransformer.from_gamma(
        config.library.transformation_gamma,
        config.library.sample_rate,
        config.library.spectrum_method,
    )
    reference = transformer.calculate_feature(
        np.zeros(window.size, dtype=np.float32),
        config.library.sample_rate,
    )
    return np.asarray(reference.edges)


def _reliability_mask(
    config: Config,
    signal_length: int,
    n_bins: int,
) -> xp.ndarray:
    """
    Per-bin factor that zeroes constant-Q bins the target signal is too short to resolve.

    A constant-Q bin needs a full wavelet of `Q * sample_rate / frequency` samples; over a
    target of `signal_length` samples only bins at or above `reliable_frequency_floor` reach
    that resolution. Zeroing the rest keeps the weighted loss on the bins both the target and
    the candidates measure. Other spectrum methods resolve every bin uniformly and keep a
    factor of one.

    Args:
        config: Configuration selecting the spectrum method and sample rate.
        signal_length: Number of samples of the matching target signal.
        n_bins: Number of spectral bins in the feature.

    Returns:
        A length-`n_bins` factor, one per resolvable bin and zero per under-resolved bin.
    """
    if config.library.spectrum_method != SpectrumMethod.CQT:
        return xp.ones(n_bins, dtype=xp.float32)

    frequencies = calculate_cqt_frequencies(n_bins, CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)
    resolvable = resolvable_bins(frequencies, config.library.sample_rate, signal_length, BINS_PER_OCTAVE)
    return xp.asarray(resolvable.astype(np.float32))
