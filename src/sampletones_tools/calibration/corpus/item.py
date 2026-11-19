from dataclasses import dataclass
from typing import FrozenSet, Optional

import numpy as np

from sampletones_core.constants.enums import ChannelName

from .families import Family
from .truth import Truth


@dataclass(frozen=True)
class CorpusItem:
    """A reference sound a calibration run reconstructs.

    Attributes:
        name: The name its files are written under.
        family: The family it belongs to, which a report and the page hold it under.
        category: The kind of decision it tests, which the reports group it by within its family.
        listed: Whether the page lists it, and so whether the run writes its audio.
        audio: The sound itself.
        truth: What the sound plays, frame by frame, where the corpus knows it.
        channels: The channels a conversion of the sound covers, or ``None`` for the run's own.
    """

    name: str
    family: Family
    category: str
    listed: bool
    audio: np.ndarray
    truth: Optional[Truth]
    channels: Optional[FrozenSet[ChannelName]]
