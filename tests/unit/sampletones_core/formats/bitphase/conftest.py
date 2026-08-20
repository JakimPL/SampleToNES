from typing import Final, Optional, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_shared.music import Tuning

NES_FREQUENCY: Final[int] = 60
REFERENCE_PITCH: Final[int] = 60


def build_features(
    volume: Sequence[int],
    *,
    arpeggio: Optional[Sequence[int]] = None,
    duty_cycle: Optional[Sequence[int]] = None,
    initial_pitch: int = REFERENCE_PITCH,
) -> Features:
    """Builds the envelopes of one channel slice, flat in every dimension left out."""
    contour = np.zeros(len(volume), dtype=int) if arpeggio is None else np.array(arpeggio, dtype=int)
    return Features(
        initial_pitch=initial_pitch,
        volume=np.array(volume, dtype=int),
        arpeggio=contour,
        pitch=None,
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else np.array(duty_cycle, dtype=int),
    )


def build_instrument(
    name: str,
    features: Features,
    *,
    channel: ChannelName = ChannelName.PULSE1,
    loop: bool = False,
) -> InstrumentExport:
    return InstrumentExport(
        name=name,
        channel=channel,
        features=features,
        loop=loop,
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


def build_sample(name: str, *instruments: InstrumentExport) -> SampleExport:
    return SampleExport(
        name=name,
        instruments=instruments,
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )
