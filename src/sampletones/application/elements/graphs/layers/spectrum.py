from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np

from sampletones.ffts import calculate_frequencies
from sampletones.library import LibraryFragment

from ....constants import VAL_SPECTRUM_GRAYSCALE_MAX, VAL_SPECTRUM_LOG_OFFSET


@dataclass(frozen=True)
class SpectrumLayer:
    fragment: LibraryFragment
    name: str
    sample_rate: int
    frame_length: int
    color: Tuple[int, int, int] = VAL_SPECTRUM_GRAYSCALE_MAX, VAL_SPECTRUM_GRAYSCALE_MAX, VAL_SPECTRUM_GRAYSCALE_MAX

    frequencies: np.ndarray = field(init=False)
    spectrum: np.ndarray = field(init=False)
    frequency_bands: Dict[int, float] = field(init=False)
    brightness_values: Dict[int, int] = field(init=False)

    def __post_init__(self):
        spectrum = self.fragment.feature
        total_energy = np.sqrt(np.sum(spectrum**2)) + VAL_SPECTRUM_LOG_OFFSET
        normalized_spectrum = spectrum / total_energy
        frequencies = calculate_frequencies(self.frame_length, self.sample_rate)
        object.__setattr__(self, "frequencies", frequencies)
        object.__setattr__(self, "spectrum", normalized_spectrum)

        frequency_bands = {}
        brightness_values = {}
        for index in range(len(self.frequencies)):
            frequency_bands[index] = self.get_frequency_band_width(index)
            brightness_values[index] = self.brightness(index)

        object.__setattr__(self, "frequency_bands", frequency_bands)
        object.__setattr__(self, "brightness_values", brightness_values)

    def __iter__(self):
        for frequency, band_width, brightness in zip(
            self.frequencies, self.frequency_bands.values(), self.brightness_values.values()
        ):
            yield frequency, band_width, brightness

    def get_frequency_band_width(self, index: int) -> float:
        frequency: float = self.frequencies[index]
        if index == 0:
            frequency_lower_bound = np.sqrt(self.frequencies[0] * self.frequencies[1])
        else:
            frequency_lower_bound = np.sqrt(self.frequencies[index - 1] * frequency)
        if index == len(self.frequencies) - 1:
            frequency_upper_bound = np.sqrt(self.frequencies[-1] ** 2 / self.frequencies[-2])
        else:
            frequency_upper_bound = np.sqrt(frequency * self.frequencies[index + 1])

        return frequency_upper_bound - frequency_lower_bound

    def brightness(self, index: int) -> int:
        energy: float = self.spectrum[index]
        return round(VAL_SPECTRUM_GRAYSCALE_MAX * energy)
