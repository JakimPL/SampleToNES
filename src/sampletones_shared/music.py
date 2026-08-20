from typing import Annotated

from pydantic import BaseModel, Field

from sampletones_shared.constants.music import (
    A4_FREQUENCY,
    A4_PITCH,
    LIMIT_MAX_PITCH,
    LIMIT_MIN_PITCH,
    MAX_A4_FREQUENCY,
    MIN_A4_FREQUENCY,
)
from sampletones_shared.utils.frequencies import pitch_to_frequency

ReferenceFrequency = Annotated[float, Field(gt=MIN_A4_FREQUENCY, lt=MAX_A4_FREQUENCY)]
ReferencePitch = Annotated[int, Field(ge=LIMIT_MIN_PITCH, le=LIMIT_MAX_PITCH)]


class Tuning(BaseModel, frozen=True, extra="forbid"):
    """Where concert pitch sits, which is what fixes the frequency every pitch sounds at.

    Equal temperament measures the whole scale from one reference, so stating that reference
    states every pitch. A reconstruction is built against a tuning of its own, and anything
    sounding or exporting its pitches reads that tuning to stay in tune with it.

    Attributes:
        a4_frequency: Frequency in Hz the reference pitch sounds at.
        a4_pitch: The pitch the reference frequency names.
    """

    a4_frequency: ReferenceFrequency = Field(
        default=A4_FREQUENCY,
    )
    a4_pitch: ReferencePitch = Field(
        default=A4_PITCH,
    )

    def frequency(self, pitch: int) -> float:
        """The frequency a pitch sounds at under this tuning.

        Args:
            pitch: The pitch to sound.

        Returns:
            float: The frequency in Hz.

        Raises:
            TypeError: If the pitch is not an integer.
            ValueError: If the pitch lies outside the range the project covers.
        """
        return pitch_to_frequency(pitch, self.a4_frequency, self.a4_pitch)
