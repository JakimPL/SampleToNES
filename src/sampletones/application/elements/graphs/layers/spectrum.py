from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Tuple

import numpy as np

from sampletones.ffts import calculate_frequencies
from sampletones.library import InstructionLibraryFragment

from ....constants.graphs import VAL_MAX_SPECTRUM_GRAYSCALE, VAL_OFFSET_SPECTRUM_LOG


@dataclass(frozen=True)
class SpectrumLayer:
    fragment: InstructionLibraryFragment[Any]
    name: str
    sample_rate: int
    frame_length: int
    color: Tuple[int, int, int] = VAL_MAX_SPECTRUM_GRAYSCALE, VAL_MAX_SPECTRUM_GRAYSCALE, VAL_MAX_SPECTRUM_GRAYSCALE

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
        for index in range(len(self.frequencies)):
            frequency_bands[index] = self.get_frequency_band_width(index)
            brightness_values[index] = self.brightness(index)

        object.__setattr__(self, "frequency_bands", frequency_bands)
        object.__setattr__(self, "brightness_values", brightness_values)

    def __iter__(self) -> Generator[Tuple[float, float, int]]:
        for item in zip(self.frequencies, self.frequency_bands.values(), self.brightness_values.values()):
            frequency: float
            band_width: float
            brightness: int
            frequency, band_width, brightness = item
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

        band_width: float = frequency_upper_bound - frequency_lower_bound
        return band_width

    def brightness(self, index: int) -> int:
        energy: float = self.spectrum[index]
        return round(VAL_MAX_SPECTRUM_GRAYSCALE * energy)
