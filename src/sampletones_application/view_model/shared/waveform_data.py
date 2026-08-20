from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class WaveformData:
    original_audio: Optional[np.ndarray]
    approximation: np.ndarray
    approximations: Dict[ChannelName, np.ndarray]
    coefficient: float
    frame_length: int

    def partials(self, channel_names: List[ChannelName]) -> np.ndarray:
        """Sums the selected generators' approximations, silent when none apply.

        The approximation sets the length, so the silent result matches the waveform even when
        no original audio is present.
        """
        if not channel_names:
            return np.zeros_like(self.approximation)

        selected_approximations = [
            self.approximations[channel_name] for channel_name in channel_names if channel_name in self.approximations
        ]

        if not selected_approximations:
            return np.zeros_like(self.approximation)

        partials: np.ndarray = np.sum(selected_approximations, axis=0)
        return partials
