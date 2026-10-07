from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PITCH, MAX_TRANSPOSE, MIN_TRANSPOSE, NUM_PERIODS
from sampletones_core.features import speaks_in_periods, transposed_reference
from sampletones_core.utils.pitch_kind import PLAYED_PITCH_VALUE_KIND, note_value_kind
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


def played_note(pitch: int) -> Note:
    """A pitch as a note cell names it, held within the notes a tonal channel plays, C-0 to B-7."""
    return Note(value=PLAYED_PITCH_VALUE_KIND.clamp(pitch))


def note_for_channel(channel_name: ChannelName, pitch: int) -> Note:
    """The note a pitch names on a channel.

    A tonal channel names the pitch itself, held within the notes it plays. The noise channel names
    the period ``pitch mod 16``, which is how FamiTracker reads a note on the noise channel, so a
    piano key picks one of its sixteen periods there.

    Args:
        channel_name: The channel the note is written on.
        pitch: The pitch a piano key names.

    Returns:
        Note: The note the channel takes.
    """
    if speaks_in_periods(channel_name):
        return Note(value=pitch % NUM_PERIODS)

    return played_note(pitch)


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
