from typing import Final

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters.feature import Features
from sampletones_core.features import (
    RESTING_REFERENCE_PERIOD,
    RESTING_REFERENCE_PITCH,
    speaks_in_periods,
)
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument

SUSTAINING_ENVELOPES: Final[InstrumentEnvelopes] = InstrumentEnvelopes(
    volume=Envelope(items=(MAX_VOLUME,), loop_point=0),
)


def new_instrument(name: str) -> Instrument:
    """An instrument a reader can place and hear straight away, before writing an envelope of its own.

    An instrument sounds the frames its envelopes describe, so one holding a single full-volume tick
    that repeats holds a note for as long as a row asks for it, at the pitch a channel added by
    hand rests on. Arpeggio and duty cycle stay the channel's until the reader writes them.

    Args:
        name: The name the voice list shows.

    Returns:
        Instrument: A voice sustaining at full volume on every channel.
    """
    return Instrument(
        name=name,
        envelopes=SUSTAINING_ENVELOPES,
    )


def instrument_from_features(
    name: str,
    features: Features,
    channel_name: ChannelName,
) -> Instrument:
    """An instrument carrying what one channel plays, in envelopes the reader can edit.

    The envelopes come across as they stand, so the voice sounds on the channel it came from what
    that channel sounded; a dimension the channel governs stays governed wherever the voice is
    placed next. Each dimension holds its final value once it runs out, the way a recorded channel
    rests on the value it last played. The channel's own reference becomes the initial pitch it was
    measured against — a period on noise and a note elsewhere — and the one the other channels read
    rests where a voice added by hand rests, so the voice stands somewhere sensible on all of them.

    Args:
        name: The name the voice list shows.
        features: The envelopes the channel plays.
        channel_name: The channel those envelopes were measured for.

    Returns:
        Instrument: The voice those envelopes describe.
    """
    return Instrument(
        name=name,
        envelopes=InstrumentEnvelopes(
            volume=features.volume,
            arpeggio=features.arpeggio,
            pitch=features.pitch if features.pitch is not None else Envelope[int](),
            hi_pitch=features.hi_pitch if features.hi_pitch is not None else Envelope[int](),
            duty_cycle=features.duty_cycle if features.duty_cycle is not None else Envelope[int](),
        ),
        initial_pitch=_initial_pitch(channel_name, features.initial_pitch),
        initial_period=_initial_period(channel_name, features.initial_pitch),
    )


def _initial_pitch(channel_name: ChannelName, reference: int) -> int:
    """The note the tonal channels measure the arpeggio against, taken from ``reference`` where it is one."""
    if speaks_in_periods(channel_name):
        return RESTING_REFERENCE_PITCH

    return reference


def _initial_period(channel_name: ChannelName, reference: int) -> int:
    """The period the noise channel measures the arpeggio against, taken from ``reference`` where it is one."""
    if speaks_in_periods(channel_name):
        return reference

    return RESTING_REFERENCE_PERIOD
