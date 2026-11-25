from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.audio.processing import decibels_to_amplitude
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import TRUTH_CONFIG_PATH


class TruthConfig(BaseModel):
    """How the corpus writes the pitch line of a synthesized sound.

    A sound counts as sounding its pitch while it stands within ``audible_decibels`` of its full level,
    since a fair test of its pitch ends where it grows quiet: a decay's tail, or a crescendo's start.
    Every synthesized sound reads this one threshold.

    Attributes:
        audible_decibels: How far below its full level a sound still counts as sounding its pitch.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    audible_decibels: float = Field(
        gt=0.0, description="How far below its full level a sound still counts as sounding its pitch."
    )

    @property
    def audible_floor(self) -> float:
        """The level against its full level a sound counts as sounding its pitch at or above."""
        return decibels_to_amplitude(-self.audible_decibels)

    @classmethod
    def load(cls) -> Self:
        """The truth settings the package ships."""
        return load_yaml_model(TRUTH_CONFIG_PATH, cls)
