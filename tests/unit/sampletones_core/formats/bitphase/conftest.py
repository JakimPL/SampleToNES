from typing import Final, Optional, Sequence

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.feature import Features
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.features.envelope import Envelope
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
    contour = (0,) * len(volume) if arpeggio is None else tuple(arpeggio)
    return Features(
        initial_pitch=initial_pitch,
        volume=Envelope(items=tuple(volume)),
        arpeggio=Envelope(items=contour),
        pitch=None,
        hi_pitch=None,
        duty_cycle=None if duty_cycle is None else Envelope(items=tuple(duty_cycle)),
    )


def build_instrument(
    name: str,
    features: Features,
    *,
    channel: ChannelName = ChannelName.PULSE1,
    loop_point: Optional[int] = None,
) -> InstrumentExport:
    return InstrumentExport(
        name=name,
        channel=channel,
        features=looping(features, loop_point),
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


def looping(features: Features, loop_point: Optional[int]) -> Features:
    """The envelopes with every dimension they write circling from ``loop_point``."""
    if loop_point is None:
        return features

    circling = features
    for feature_key, envelope in features.envelopes.items():
        if envelope.written:
            circling = circling.with_envelope(feature_key, envelope.model_copy(update={"loop_point": loop_point}))

    return circling
