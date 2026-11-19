from typing import Self

from pydantic import ConfigDict, model_validator

from sampletones_core.constants.general import PlayedPitch
from sampletones_core.data import DataModel


class PitchRange(DataModel):
    """The notes, lowest to highest, a library holds tonal instructions for.

    The range shapes what a library holds, so it takes part in the library's name beside the
    library settings and travels in the library's file.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: PlayedPitch
    max_pitch: PlayedPitch

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.min_pitch > self.max_pitch:
            raise ValueError(f"min_pitch {self.min_pitch} stands above max_pitch {self.max_pitch}")

        return self

    @property
    def pitches(self) -> range:
        return range(self.min_pitch, self.max_pitch + 1)
