from dataclasses import dataclass
from typing import FrozenSet, Optional

import numpy as np

from sampletones_core.constants.enums import ChannelName

from .truth import Truth


@dataclass(frozen=True)
class CorpusItem:
    """A reference sound a calibration run reconstructs.

    Attributes:
        name: The name its files are written under.
        category: The kind of decision it tests, which the reports group it by.
        audio: The sound itself.
        truth: What the sound plays, frame by frame, where the corpus knows it.
        channels: The channels a conversion of the sound covers, or ``None`` for the run's own.
    """

    name: str
    category: str
    audio: np.ndarray
    truth: Optional[Truth]
    channels: Optional[FrozenSet[ChannelName]]
