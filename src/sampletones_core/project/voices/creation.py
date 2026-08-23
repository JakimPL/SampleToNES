from typing import Final, Optional, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters.feature import Features
from sampletones_core.features import (
    RESTING_REFERENCE_PERIOD,
    RESTING_REFERENCE_PITCH,
    speaks_in_periods,
)
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT

SUSTAINING_ENVELOPES: Final[InstrumentEnvelopes] = InstrumentEnvelopes(volume=(MAX_VOLUME,))


def new_instrument(name: str) -> Instrument:
    """An instrument a reader can place and hear straight away, before writing an envelope of its own.

    An instrument sounds the frames its envelopes describe, so one holding a single full-volume tick
    that repeats holds a note for as long as a row asks for it, at the roots a channel added by
    hand rests on. Arpeggio and duty cycle stay the channel's until the reader writes them.

    Args:
        name: The name the voice list shows.

    Returns:
        Instrument: A voice sustaining at full volume on every channel.
    """
    return Instrument(
        name=name,
        envelopes=SUSTAINING_ENVELOPES,
        loop_point=WHOLE_LOOP_POINT,
    )


def instrument_from_features(
    name: str,
    features: Features,
    channel_name: ChannelName,
    *,
    loop_point: Optional[int],
) -> Instrument:
    """An instrument carrying what one channel plays, in envelopes the reader can edit.

    The envelopes come across as they stand, so the voice sounds on the channel it came from what
    that channel sounded; a dimension the channel governs stays governed wherever the voice is
    placed next. The channel's own reference becomes the root it was measured against — a period on
    noise and a note elsewhere — and the root the other channels read rests where a voice added by
    hand rests, so the voice stands somewhere sensible on all of them.

    Args:
        name: The name the voice list shows.
        features: The envelopes the channel plays.
        channel_name: The channel those envelopes were measured for.
        loop_point: The tick the envelopes repeat from, or ``None`` where they play once.

    Returns:
        Instrument: The voice those envelopes describe.
    """
    return Instrument(
        name=name,
        envelopes=InstrumentEnvelopes(
            volume=_envelope(features.volume),
            arpeggio=_envelope(features.arpeggio),
            duty_cycle=_envelope(features.duty_cycle),
        ),
        root_pitch=_root_pitch(channel_name, features.initial_pitch),
        root_period=_root_period(channel_name, features.initial_pitch),
        loop_point=loop_point,
    )


def _root_pitch(channel_name: ChannelName, reference: int) -> int:
    """The note the tonal channels measure the arpeggio against, taken from ``reference`` where it is one."""
    if speaks_in_periods(channel_name):
        return RESTING_REFERENCE_PITCH

    return reference


def _root_period(channel_name: ChannelName, reference: int) -> int:
    """The period the noise channel measures the arpeggio against, taken from ``reference`` where it is one."""
    if speaks_in_periods(channel_name):
        return reference

    return RESTING_REFERENCE_PERIOD


def _envelope(items: Optional[np.ndarray]) -> Tuple[int, ...]:
    """One dimension as a voice states it, empty where the channel governs it."""
    if items is None:
        return ()

    return tuple(int(item) for item in items)
