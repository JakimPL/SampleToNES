from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.tracker_playback.paths import SETTINGS_PATH


class PlaybackSettings(BaseModel):
    """How a tracker playback check reports what it finds.

    Attributes:
        examples_per_difference: How many ticks a difference shows as examples at most: the first it
            strikes, then the later rows where both sides sound new values.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    examples_per_difference: int = Field(..., ge=1)

    @classmethod
    def load(cls) -> Self:
        """The settings the package ships."""
        return load_yaml_model(SETTINGS_PATH, cls)
