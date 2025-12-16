from dataclasses import dataclass
from typing import NamedTuple

from sampletones.typehints import Color


class ThemeColor(NamedTuple):
    key: int
    color: Color
    category: int = 0


class ThemeStyle(NamedTuple):
    key: int
    x: float
    y: float = -1
    category: int = 0


@dataclass(frozen=True)
class ThemeParameter:
    item_type: int
    enabled_state: bool = True
