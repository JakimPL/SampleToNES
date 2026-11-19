from typing import Dict, List, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_core.constants.enums import ChannelName
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import SEQUENCES_CONFIG_PATH
from sampletones_tools.corpus.written import FrameRun


class SequenceConfig(BaseModel):
    """A sequence written out as NES frames: what each channel plays, frame by frame.

    Attributes:
        name: The name its files are written under.
        category: The kind of decision it tests.
        channels: The frames each channel plays, as runs of alike frames, every channel as long as
            the others.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    category: str
    channels: Dict[ChannelName, List[FrameRun]] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_channels_last_alike(self) -> Self:
        lengths = {channel.value: sum(run.count for run in runs) for channel, runs in self.channels.items()}
        if len(set(lengths.values())) > 1:
            raise ValueError(f"Every channel of {self.name!r} must last as many frames as the others: {lengths}")

        return self


class SequencesConfig(BaseModel):
    """The sequences written out as NES frames, whose conversions are measured against them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: List[SequenceConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_unique_names(self) -> Self:
        names = [item.name for item in self.items]
        if len(set(names)) != len(names):
            raise ValueError("Every written sequence must have a name of its own")

        return self

    @classmethod
    def load(cls) -> Self:
        """The written sequences the package ships."""
        return load_yaml_model(SEQUENCES_CONFIG_PATH, cls)
