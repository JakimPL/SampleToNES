from pydantic import BaseModel, Field

from sampletones_core.constants.general import MAX_PITCH


class PlayingBehavior(BaseModel, extra="forbid", frozen=True):
    """How a key played live reaches a recording.

    Attributes:
        sample_root: The key that plays a recording as it was recorded; every other key steps it by the
            semitones it stands from this one.
    """

    sample_root: int = Field(..., ge=0, le=MAX_PITCH)
