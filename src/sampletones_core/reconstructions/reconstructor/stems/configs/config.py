from typing import List, Self

from pydantic import ConfigDict, Field, model_validator

from sampletones_core.constants.algorithm import (
    DEFAULT_STEMS_CHANNEL_CAP,
)
from sampletones_core.data import DataModel
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy


class StemsConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: List[StemEntry] = Field(
        default_factory=list,
        description="The competing stems and the channels each may occupy",
    )
    hierarchy: StemsHierarchy = Field(
        default_factory=StemsHierarchy,
        description="The precedence structure of the stems assignment",
    )
    channel_cap: int = Field(
        default=DEFAULT_STEMS_CHANNEL_CAP,
        ge=1,
        description="The most channels one stem holds per frame",
    )

    @model_validator(mode="after")
    def _validate_unique_entry_ids(self) -> Self:
        ids = [entry.id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise ValueError("Stem entries must have unique ids")

        return self
