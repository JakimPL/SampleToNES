from dataclasses import dataclass
from functools import cached_property
from typing import Final, List, Sequence, Tuple

import numpy as np

from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.fft.fft import calculate_weights_from_edges
from sampletones_core.fft.spectrum.cqt import calculate_cqt_spectrum_columns
from sampletones_core.fft.spectrum.fft import (
    calculate_fft_spectrum,
    calculate_log_spaced_fft_spectrum,
)
from sampletones_core.fft.window.window import Window
from sampletones_core.structures.histogram import Histogram

PROBE_TONE_AMPLITUDE: Final[float] = 0.5
PROBE_NOISE_SIGMA: Final[float] = 0.1
PROBE_NOISE_SEED: Final[int] = 0
PROBE_CQT_SIGNAL_SECONDS: Final[int] = 1


def sine_tone(frequency: float, length: int, sample_rate: int, amplitude: float) -> np.ndarray:
    """
    Render a pure sine tone for spectral response measurements.

    Args:
        frequency: Tone frequency in Hz.
        length: Number of samples.
        sample_rate: Sampling rate in Hz.
        amplitude: Peak amplitude.

    Returns:
        Tone samples as a float32 array of the requested length.
    """
    samples = np.arange(length)
    return (amplitude * np.sin(2.0 * np.pi * frequency * samples / sample_rate)).astype(np.float32)


def bin_center_frequencies(spectrum: Histogram) -> np.ndarray:
    """
    Center frequency of every bin of a spectrum histogram.

    Args:
        spectrum: Spectrum histogram with frequency edges.

    Returns:
        Bin center frequencies in Hz, one per bin.
    """
    edges = np.asarray(spectrum.edges, dtype=np.float64)
    return (edges[:-1] + edges[1:]) / 2.0


def bin_value_at(spectrum: Histogram, frequency: float) -> float:
    """
    Value of the single bin whose center lies closest to a frequency.

    Args:
        spectrum: Spectrum histogram.
        frequency: Query frequency in Hz.

    Returns:
        The value of the nearest bin.
    """
    centers = bin_center_frequencies(spectrum)
    index = int(np.argmin(np.abs(centers - frequency)))
    return float(spectrum.values[index])


def band_energy(spectrum: Histogram, frequency: float, *, radius: int) -> float:
    """
    Total energy in the bins surrounding a frequency.

    Summing over a small neighborhood captures the full response of a tone whose
    energy spreads over the main lobe of the analysis window, keeping the measure
    robust to scalloping between bin centers.

    Args:
        spectrum: Spectrum histogram.
        frequency: Center frequency of the band in Hz.
        radius: Number of bins included on each side of the nearest bin.

    Returns:
        Sum of the values over the ``2 * radius + 1`` bins around the frequency.
    """
    centers = bin_center_frequencies(spectrum)
    index = int(np.argmin(np.abs(centers - frequency)))
    lower = max(0, index - radius)
    upper = index + radius + 1
    return float(np.sum(spectrum.values[lower:upper]))


def octave_weight_shares(
    edges: np.ndarray,
    *,
    perceptual_exponent: float,
    bands: Sequence[Tuple[float, float]],
) -> List[float]:
    """
    Share of the total criterion weight allocated to each frequency band.

    Runs the production weighting on the given bin edges and aggregates the
    normalized weights per band, which measures how the criterion distributes
    attention over the spectrum for a given frequency axis.

    Args:
        edges: Strictly increasing bin edges in Hz.
        perceptual_exponent: Power applied to the A-weighting curve.
        bands: Frequency intervals ``(lower, upper)`` in Hz.

    Returns:
        One weight share per band, in band order.
    """
    weights = calculate_weights_from_edges(np.asarray(edges, dtype=np.float64), perceptual_exponent)
    centers = (np.asarray(edges[:-1], dtype=np.float64) + np.asarray(edges[1:], dtype=np.float64)) / 2.0
    return [float(np.sum(weights[(centers >= lower) & (centers < upper)])) for lower, upper in bands]


@dataclass(frozen=True)
class SpectrumProbe:
    """
    Measures how one spectrum method responds to elementary signals.

    Wraps a library configuration (sample rate, NES frequency, spectrum method) and
    produces single-frame spectra of pure tones and white noise through the same
    windowing path the reconstruction pipeline uses, so scaling properties measured
    here transfer directly to the matching criterion.
    """

    sample_rate: int
    nes_frequency: int
    method: SpectrumMethod

    @cached_property
    def config(self) -> InstructionsLibraryConfig:
        return InstructionsLibraryConfig(
            nes_frequency=self.nes_frequency,
            sample_rate=self.sample_rate,
            spectrum_method=self.method,
        )

    @cached_property
    def window(self) -> Window:
        return Window.from_config(self.config)

    def tone_spectrum(self, frequency: float, *, amplitude: float = PROBE_TONE_AMPLITUDE) -> Histogram:
        """
        Single-frame spectrum of a pure tone.

        Args:
            frequency: Tone frequency in Hz.
            amplitude: Peak amplitude of the tone.

        Returns:
            The frame spectrum of the tone under this probe's method.
        """
        audio = sine_tone(frequency, self.signal_length, self.sample_rate, amplitude)
        return self.frame_spectrum(audio)

    def mean_noise_spectrum(
        self,
        *,
        draws: int,
        sigma: float = PROBE_NOISE_SIGMA,
        seed: int = PROBE_NOISE_SEED,
    ) -> Histogram:
        """
        Average single-frame spectrum of white noise over several draws.

        Averaging reduces the per-bin variance of the noise estimate, so scaling
        comparisons between bins reflect the method rather than a single draw.

        Args:
            draws: Number of independent noise realizations to average.
            sigma: Standard deviation of the noise.
            seed: Seed of the random generator.

        Returns:
            The mean frame spectrum over all draws.
        """
        generator = np.random.default_rng(seed)
        spectra: List[Histogram] = []
        for _ in range(draws):
            audio = (sigma * generator.standard_normal(self.signal_length)).astype(np.float32)
            spectra.append(self.frame_spectrum(audio))

        values = np.mean([spectrum.values for spectrum in spectra], axis=0).astype(np.float32)
        return Histogram(edges=spectra[0].edges, values=values)

    def frame_spectrum(self, audio: np.ndarray) -> Histogram:
        """
        Spectrum of one frame of audio under this probe's method.

        The windowed methods analyze one envelope-weighted window; the constant-Q
        method transforms the whole signal and reports its central column, matching
        how the feature extractors position a frame within its context.

        Args:
            audio: Input audio of ``signal_length`` samples.

        Returns:
            The frame spectrum histogram.

        Raises:
            ValueError: If the spectrum method is unsupported.
        """
        match self.method:
            case SpectrumMethod.FFT:
                return calculate_fft_spectrum(audio * self.window.envelope, self.sample_rate, self.window.size)
            case SpectrumMethod.LOG_SPACED_FFT:
                return calculate_log_spaced_fft_spectrum(
                    audio * self.window.envelope,
                    self.sample_rate,
                    self.window.size,
                )
            case SpectrumMethod.CQT:
                columns = calculate_cqt_spectrum_columns(audio, self.sample_rate, self.config.frame_length)
                return columns[len(columns) // 2]
            case _:
                raise ValueError(f"Unsupported spectrum method: {self.method}")

    @property
    def signal_length(self) -> int:
        """
        Number of samples a probe signal spans.

        The windowed methods analyze exactly one window; the constant-Q method
        receives a full second so the longest wavelets see complete context around
        the central column.
        """
        if self.method == SpectrumMethod.CQT:
            return PROBE_CQT_SIGNAL_SECONDS * self.sample_rate

        return int(self.window.size)
