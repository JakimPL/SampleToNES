from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class WaveformData:
    """What the waveform display draws of a document and the player plays, for one hearing of it.

    Attributes:
        original_audio: The recordings heard mixed into one waveform, ``None`` while no recording loads.
        approximation: Every channel in play mixed, the frames of the recordings left out silenced.
        playing: The channels kept on mixed the same way, which is what plays and is drawn.
        coefficient: The level the original is scaled by to stand beside the approximation.
        frame_length: How many samples one frame spans.
        sample_rate: How many samples one second spans.
    """

    original_audio: Optional[np.ndarray]
    approximation: np.ndarray
    playing: np.ndarray
    coefficient: float
    frame_length: int
    sample_rate: int
