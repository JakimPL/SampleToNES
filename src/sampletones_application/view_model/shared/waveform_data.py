from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from sampletones_core.constants.enums import GeneratorName


@dataclass(frozen=True)
class WaveformData:
    original_audio: np.ndarray
    approximation: np.ndarray
    approximations: Dict[GeneratorName, np.ndarray]
    coefficient: float
    frame_length: int

    def partials(self, generator_names: List[GeneratorName]) -> np.ndarray:
        """Sums the selected generators' approximations, silent when none apply."""
        if not generator_names:
            return np.zeros_like(self.original_audio)

        selected_approximations = [
            self.approximations[generator_name]
            for generator_name in generator_names
            if generator_name in self.approximations
        ]

        if not selected_approximations:
            return np.zeros_like(self.original_audio)

        partials: np.ndarray = np.sum(selected_approximations, axis=0)
        return partials
