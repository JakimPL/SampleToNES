from dataclasses import dataclass, field
from typing import Any, Generator, Tuple

import numpy as np

from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_core.library import InstructionLibraryFragment
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.types.application import Color


@dataclass(frozen=True)
class SpectrumLayer(Layer):
    data: InstructionLibraryFragment[Any]
    name: str
    color_dim: Color
    color_bright: Color
    max_display_bins: int

    spectrum: Histogram = field(init=False)
    frequencies: np.ndarray = field(init=False)
    bandwidths: np.ndarray = field(init=False)
    brightness: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        spectrum = self.data.feature
        n_bins = min(len(spectrum), self.max_display_bins)
        if n_bins < len(spectrum):
            spectrum = Histogram(edges=spectrum.edges[: n_bins + 1], values=spectrum.values[:n_bins])

        values = spectrum.values / np.max(spectrum.values)
        frequencies = (spectrum.edges[:-1] + spectrum.edges[1:]) / 2
        bandwidths = spectrum.edges[1:] - spectrum.edges[:-1]
        brightness = np.round(values * 255).astype(np.uint8)

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
