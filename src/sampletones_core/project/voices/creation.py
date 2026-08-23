from typing import Final

from sampletones_core.constants.general import MAX_VOLUME
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
