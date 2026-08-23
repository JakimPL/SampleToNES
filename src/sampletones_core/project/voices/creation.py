from typing import Final

from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.project.voices.envelopes import ShapeEnvelopes
from sampletones_core.project.voices.loop import WHOLE_LOOP_POINT
from sampletones_core.project.voices.shape import Shape

SUSTAINING_ENVELOPES: Final[ShapeEnvelopes] = ShapeEnvelopes(volume=(MAX_VOLUME,))


def new_shape(name: str) -> Shape:
    """A shape a reader can place and hear straight away, before writing an envelope of its own.

    A shape sounds the frames its envelopes describe, so one holding a single full-volume tick
    that repeats holds a note for as long as a row asks for it, at the roots a channel added by
    hand rests on. Arpeggio and duty cycle stay the channel's until the reader writes them.

    Args:
        name: The name the voice list shows.

    Returns:
        Shape: A voice sustaining at full volume on every channel.
    """
    return Shape(
        name=name,
        envelopes=SUSTAINING_ENVELOPES,
        loop_point=WHOLE_LOOP_POINT,
    )
