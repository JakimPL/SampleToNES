from pydantic import ConfigDict, Field

from sampletones_core.data import DataModel
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


class StemEntry(DataModel):
    """One stem a run competes for channels with: the id it is recorded under, and its settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: int = Field(
        ...,
        description="Identifier of the stem the hierarchy references",
    )
    settings: StemSettings = Field(
        ...,
        description="What the recording behind this stem is converted with",
    )
