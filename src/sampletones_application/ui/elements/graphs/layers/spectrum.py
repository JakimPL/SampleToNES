from dataclasses import dataclass, field
from typing import Any, Generator, Tuple

import numpy as np

from sampletones_application.constants.graphs import VAL_MAX_SPECTRUM_DISPLAY_BINS, VAL_MAX_SPECTRUM_GRAYSCALE
from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_core.constants.spectrum import CQT_CUTOFF_FREQUENCY
from sampletones_core.fft.utils import to_log_even_bands
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.types.application import Color


@dataclass(frozen=True)
class SpectrumLayer(Layer):
    data: InstructionLibraryFragment[Any]
    name: str
    sample_rate: int
    frame_length: int
    color: Color = VAL_MAX_SPECTRUM_GRAYSCALE, VAL_MAX_SPECTRUM_GRAYSCALE, VAL_MAX_SPECTRUM_GRAYSCALE

    spectrum: Histogram = field(init=False)
    frequencies: np.ndarray = field(init=False)
    bandwidths: np.ndarray = field(init=False)
    brightness: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        spectrum = self.data.feature
        n_bins = min(len(self.data.feature), VAL_MAX_SPECTRUM_DISPLAY_BINS)
        bands = to_log_even_bands(spectrum.edges, CQT_CUTOFF_FREQUENCY, n_bins)
        spectrum = spectrum.rebin(bands)

        values = spectrum.values / np.max(spectrum.values)
        frequencies = np.sqrt(spectrum.edges[:-1] * spectrum.edges[1:])
        bandwidths = frequencies[1:] - frequencies[:-1]
        brightness = np.round(values * VAL_MAX_SPECTRUM_GRAYSCALE).astype(np.uint8)

        object.__setattr__(self, "spectrum", spectrum)
        object.__setattr__(self, "frequencies", frequencies)
        object.__setattr__(self, "bandwidths", bandwidths)
        object.__setattr__(self, "brightness", brightness)

        object.__setattr__(self, "x_data", np.array((0.0, 1.0), dtype=np.float32))
        object.__setattr__(self, "y_data", np.array(frequencies, dtype=np.float32))

    def __iter__(self) -> Generator[Tuple[float, float, int]]:
        for item in zip(self.frequencies, self.bandwidths, self.brightness):
            frequency: float
            bandwidth: float
            brightness: int
            frequency, bandwidth, brightness = item
            yield frequency, bandwidth, brightness
