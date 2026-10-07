from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PITCH, MAX_TRANSPOSE, MIN_TRANSPOSE
from sampletones_core.features import transposed_reference
from sampletones_core.utils.pitch_kind import note_value_kind
from sampletones_shared.utils.arrays import clamp


class Note(BaseModel):
    """A pitch cell naming the note the channel sounds.

    The value is the pitch on a tonal channel and the period on noise, the two ranges standing
    apart, so a note reads the same whichever voice the row names and keeps its pitch when the
    voice changes.

    Attributes:
        value: The pitch, or the period, the channel sounds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["note"] = "note"
    value: int = Field(..., ge=0, le=MAX_PITCH)


class Step(BaseModel):
    """A pitch cell naming the step from the voice's own reference.

    A sample measures the step from the pitch it was recorded at, and an instrument from its initial
    pitch, so the same step moves every voice by the same interval from where it rests.

    Attributes:
        value: The semitones, or the periods on noise, the row moves the voice by.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["step"] = "step"
    value: int = Field(..., ge=MIN_TRANSPOSE, le=MAX_TRANSPOSE)


RowPitch = Annotated[Union[Note, Step], Field(discriminator="kind")]


def step_of(pitch: RowPitch, *, reference: int) -> int:
    """The step from a voice's reference that a pitch cell asks for.

    A step states it outright, and a note is measured from the reference, so both faces reach the
    channel as the one offset it sounds a voice at.

    Args:
        pitch: The pitch the row states.
        reference: The value the voice rests at on the channel.

    Returns:
        int: The semitones, or the periods on noise, from the reference.
    """
    match pitch:
        case Step():
            return pitch.value
        case Note():
            return pitch.value - reference


def sounded_pitch(
    channel_name: ChannelName,
    pitch: RowPitch,
    *,
    reference: int,
) -> int:
    """Where a voice sounds on a channel once a pitch cell has moved it.

    Args:
        channel_name: The channel sounding the voice.
        pitch: The pitch the row states.
        reference: The value the voice rests at on the channel.

    Returns:
        int: The pitch, or the period, the channel sounds.
    """
    return transposed_reference(channel_name, reference, step_of(pitch, reference=reference))


def clamped_note(channel_name: ChannelName, value: int) -> Note:
    """A note held inside the range a channel plays: its notes from C-0 up, or its sixteen periods."""
    return Note(value=note_value_kind(channel_name).clamp(value))


def clamped_step(value: int) -> Step:
    """A step held inside the range a row accepts."""
    return Step(value=int(clamp(value, MIN_TRANSPOSE, MAX_TRANSPOSE)))


def shifted_pitch(
    pitch: RowPitch,
    delta: int,
    channel_name: ChannelName,
) -> RowPitch:
    """A pitch moved by ``delta`` on its own face: a note to another note, a step to another step."""
    match pitch:
        case Step():
            return clamped_step(pitch.value + delta)
        case Note():
            return clamped_note(channel_name, pitch.value + delta)
