from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from sampletones_core.audio.mixing import align, mix
from sampletones_core.constants.enums import ChannelName


@dataclass(frozen=True)
class WaveformData:
    """What the waveform display draws of a document: the audio each channel plays and their mix.

    ``approximation`` is the mix of ``approximations``, which is what lets a reading over every
    channel answer with the mix itself.
    """

    original_audio: Optional[np.ndarray]
    approximation: np.ndarray
    approximations: Dict[ChannelName, np.ndarray]
    coefficient: float
    frame_length: int
    sample_rate: int

    def partials(self, channel_names: List[ChannelName]) -> np.ndarray:
        """Sums the selected channels' approximations, silent when none apply.

        A selection covering every channel answers the mix the data already holds. A narrower
        one is summed in channel order whatever order it was given in, so the same choice reads
        the same samples. The approximation sets the length, so the silent result matches the
        waveform even when no original audio is present, and each selected approximation pads to
        that length before the sum, so a channel that ends early leaves the tail in silence.
        """
        selected = [channel_name for channel_name in ChannelName.items() if channel_name in channel_names]
        selected_approximations = [
            self.approximations[channel_name] for channel_name in selected if channel_name in self.approximations
        ]
        if not selected_approximations:
            return np.zeros_like(self.approximation)

        if len(selected_approximations) == len(self.approximations):
            return self.approximation

        return mix(align(selected_approximations, len(self.approximation)))
