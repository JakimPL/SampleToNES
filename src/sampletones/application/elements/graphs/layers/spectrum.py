from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Tuple

import numpy as np

from sampletones.ffts import calculate_frequencies
from sampletones.library import InstructionLibraryFragment

from ....constants.graphs import (
    VAL_MAX_SPECTRUM_DISPLAY_BINS,
    VAL_MAX_SPECTRUM_GRAYSCALE,
    VAL_OFFSET_SPECTRUM_LOG,
)


@dataclass(frozen=True)
class SpectrumLayer:
    fragment: InstructionLibraryFragment[Any]
    name: str
    sample_rate: int
    frame_length: int
    color: Tuple[int, int, int] = VAL_MAX_SPECTRUM_GRAYSCALE, VAL_MAX_SPECTRUM_GRAYSCALE, VAL_MAX_SPECTRUM_GRAYSCALE

    redistribute_to_log_bins: bool = True

    frequencies: np.ndarray = field(init=False)
    spectrum: np.ndarray = field(init=False)
    frequency_bands: Dict[int, float] = field(init=False)
    brightness_values: Dict[int, int] = field(init=False)

    def __post_init__(self) -> None:
        spectrum = self.fragment.feature
        total_energy = np.sqrt(np.sum(spectrum**2)) + VAL_OFFSET_SPECTRUM_LOG
        normalized_spectrum = spectrum / total_energy
        frequencies = calculate_frequencies(self.frame_length, self.sample_rate)
        object.__setattr__(self, "frequencies", frequencies)
        object.__setattr__(self, "spectrum", normalized_spectrum)

        frequency_bands = {}
        brightness_values = {}

        if self.redistribute_to_log_bins:
            redistributed_spectrum, redistributed_frequencies, redistributed_frequency_bands = (
                self._redistribute_energy_bins()
            )
            object.__setattr__(self, "spectrum", redistributed_spectrum)
            object.__setattr__(self, "frequencies", redistributed_frequencies)
            frequency_bands = redistributed_frequency_bands
            for index in range(len(self.frequencies)):
                brightness_values[index] = self._brightness(index)
        else:
            for index in range(len(self.frequencies)):
                frequency_bands[index] = self._get_frequency_band_width(index)
                brightness_values[index] = self._brightness(index)

        object.__setattr__(self, "frequency_bands", frequency_bands)
        object.__setattr__(self, "brightness_values", brightness_values)

    def __iter__(self) -> Generator[Tuple[float, float, int]]:
        for item in zip(self.frequencies, self.frequency_bands.values(), self.brightness_values.values()):
            frequency: float
            band_width: float
            brightness: int
            frequency, band_width, brightness = item
            yield frequency, band_width, brightness

    def _redistribute_energy_bins(self) -> Tuple[np.ndarray, np.ndarray, Dict[int, float]]:
        bins = min(len(self.spectrum), VAL_MAX_SPECTRUM_DISPLAY_BINS)
        min_frequency = self.frequencies[0]
        max_frequency = self.frequencies[-1]

        new_frequencies = np.logspace(
            np.log10(min_frequency),
            np.log10(max_frequency),
            bins,
        )

        frequency_step = self.frequencies[1] - self.frequencies[0]
        linear_bin_edges = np.concatenate(
            [self.frequencies - frequency_step / 2, [self.frequencies[-1] + frequency_step / 2]]
        )

        log_bin_edges = np.zeros(bins + 1)
        log_bin_edges[0] = new_frequencies[0] / np.sqrt(new_frequencies[1] / new_frequencies[0])
        log_bin_edges[-1] = new_frequencies[-1] * np.sqrt(new_frequencies[-1] / new_frequencies[-2])
        for i in range(1, bins):
            log_bin_edges[i] = np.sqrt(new_frequencies[i - 1] * new_frequencies[i])

        new_spectrum = np.zeros(bins)
        new_frequency_bands = {}

        for i in range(bins):
            lower_edge = log_bin_edges[i]
            upper_edge = log_bin_edges[i + 1]

            overlapping_bins = np.where((linear_bin_edges[1:] > lower_edge) & (linear_bin_edges[:-1] < upper_edge))[0]

            for j in overlapping_bins:
                overlap_lower = max(lower_edge, linear_bin_edges[j])
                overlap_upper = min(upper_edge, linear_bin_edges[j + 1])
                overlap_width = overlap_upper - overlap_lower

                linear_bin_width = linear_bin_edges[j + 1] - linear_bin_edges[j]
                fraction = overlap_width / linear_bin_width

                new_spectrum[i] += self.spectrum[j] * fraction

            new_frequency_bands[i] = upper_edge - lower_edge

        return new_spectrum, new_frequencies, new_frequency_bands

    def _get_frequency_band_width(self, index: int) -> float:
        frequency: float = self.frequencies[index]
        if index == 0:
            frequency_lower_bound = np.sqrt(self.frequencies[0] * self.frequencies[1])
        else:
            frequency_lower_bound = np.sqrt(self.frequencies[index - 1] * frequency)
        if index == len(self.frequencies) - 1:
            frequency_upper_bound = np.sqrt(self.frequencies[-1] ** 2 / self.frequencies[-2])
        else:
            frequency_upper_bound = np.sqrt(frequency * self.frequencies[index + 1])

        band_width: float = frequency_upper_bound - frequency_lower_bound
        return band_width

    def _brightness(self, index: int) -> int:
        energy: float = self.spectrum[index]
        return round(VAL_MAX_SPECTRUM_GRAYSCALE * energy)
