from typing import List

from pydantic import ConfigDict, Field

from sampletones_core.constants.algorithm import (
    DEFAULT_STEMS_HIERARCHY_MODE,
)
from sampletones_core.constants.enums import HierarchyMode
from sampletones_core.data import DataModel


class StemsHierarchy(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    levels: List[List[int]] = Field(
        default_factory=list,
        description="Stem id levels, picked in the order listed",
    )
    mode: HierarchyMode = Field(
        default=DEFAULT_STEMS_HIERARCHY_MODE,
        description="Whether levels alternate per round or exhaust in order",
    )
