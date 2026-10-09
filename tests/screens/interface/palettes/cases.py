from dataclasses import dataclass
from typing import Dict

from automation.boundaries.highlights import HighlightPlace
from automation.palettes import Color


@dataclass(frozen=True)
class Painted:
    """Every color the interface holds at one moment.

    Attributes:
        held: The colors DearPyGui holds for items and themes, by item.
        highlights: The highlight colors laid on the tables, by place.
    """

    held: Dict[str, Color]
    highlights: Dict[HighlightPlace, Color]
