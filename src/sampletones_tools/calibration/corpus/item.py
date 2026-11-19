from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig

from .families import Family
from .truth import Truth


@dataclass(frozen=True)
class StemsSources:
    """A sound held as stems: one recording per entry of the setup they are converted under.

    Attributes:
        sources: The recordings, one per entry, in the setup's entry order.
        config: The stems setup the recordings are converted under.
    """

    sources: Tuple[np.ndarray, ...]
    config: StemsConfig


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
        stems: The stems the sound is held as, or ``None`` for a sound converted as one recording.
            The audio is then their mix.
    """

    name: str
    family: Family
    category: str
    listed: bool
    audio: np.ndarray
    truth: Optional[Truth]
    channels: Optional[FrozenSet[ChannelName]]
    stems: Optional[StemsSources]
