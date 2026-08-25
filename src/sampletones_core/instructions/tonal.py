from abc import ABC

from pydantic import Field

from sampletones_core.constants.general import (
    HI_PITCH_FACTOR,
    MAX_PITCH,
    MIN_PITCH,
    PITCH_BEND_MAX,
    PITCH_BEND_MIN,
)

from .instruction import Instruction


class TonalInstruction(Instruction, ABC):
    """An instruction naming a note, sounded through a timer the frame may bend.

    The pulse and triangle channels reach a pitch by loading a timer, and the timer grid is finer
    than the semitone grid everywhere below the top of the range: a step spans well under a cent
    at the lowest notes and widens to a whole semitone at the highest. A frame therefore states
    the note it plays and, beside it, the offset in timer steps that carries it off the
    equal-tempered grid — the two dimensions FamiTracker writes as its pitch and hi-pitch
    sequences, one step apiece and one step of sixteen.

    Attributes:
        pitch: The note the frame names.
        detune: Timer steps the frame is bent by, one step per unit.
        coarse_detune: Timer steps the frame is bent by, sixteen steps per unit.
    """

    pitch: int = Field(..., ge=MIN_PITCH, le=MAX_PITCH, description="The note the frame names")
    detune: int = Field(
        default=0,
        ge=PITCH_BEND_MIN,
        le=PITCH_BEND_MAX,
        description="Timer steps the frame is bent by, one step per unit",
    )
    coarse_detune: int = Field(
        default=0,
        ge=PITCH_BEND_MIN,
        le=PITCH_BEND_MAX,
        description="Timer steps the frame is bent by, sixteen steps per unit",
    )

    @property
    def timer_offset(self) -> int:
        """The timer steps this frame stands away from its note, both dimensions together."""
        return self.detune + HI_PITCH_FACTOR * self.coarse_detune

    @property
    def bent(self) -> bool:
        """Whether the frame sounds anywhere other than its note's own timer."""
        return self.timer_offset != 0
