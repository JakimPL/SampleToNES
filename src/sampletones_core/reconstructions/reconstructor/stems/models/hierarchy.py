from dataclasses import dataclass
from typing import Tuple

from sampletones_core.constants.enums import HierarchyMode


@dataclass(frozen=True)
class StemHierarchy:
    """
    The precedence structure of a stems assignment: stems grouped into levels that
    pick in order, with a mode choosing how picks alternate between levels.
    """

    levels: Tuple[Tuple[int, ...], ...]
    mode: HierarchyMode
