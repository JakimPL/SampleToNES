from typing import Dict, Final, List, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt, model_validator

from sampletones_core.constants.enums import ChannelName
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import CHORDS_CONFIG_PATH
from sampletones_tools.corpus.written import FrameValue

from .names import require_unique_names

CHORD_SIZE: Final[int] = 2


class ChordConfig(BaseModel):
    """Channels held together on one frame each, as one reference sound.

    Attributes:
        name: The name its files are written under.
        category: The kind of decision it tests.
        listed: Whether the page lists it.
        frames: The instruction each channel holds, in the fields its instruction takes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    category: str
    listed: bool
    frames: Dict[ChannelName, Dict[str, FrameValue]] = Field(min_length=CHORD_SIZE)


class ChordsConfig(BaseModel):
    """The chords the channels hold together, each held and then silent for one shared length.

    Attributes:
        sounding_frames: How many frames each chord holds.
        silent_frames: How many frames of silence follow it.
        chords: The chords, in the order the corpus holds them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sounding_frames: PositiveInt
    silent_frames: NonNegativeInt
    chords: List[ChordConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_names(self) -> Self:
        require_unique_names([chord.name for chord in self.chords], "chord")
        return self

    @classmethod
    def load(cls) -> Self:
        """The chords the package ships."""
        return load_yaml_model(CHORDS_CONFIG_PATH, cls)
