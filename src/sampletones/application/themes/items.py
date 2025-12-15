from dataclasses import dataclass
from typing import Dict, List, NamedTuple, Union

from pydantic import BaseModel, ConfigDict, Field

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


class ThemeItems(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    items: Dict[ThemeParameter, Union[List[ThemeColor], List[ThemeStyle], List[Union[ThemeColor, ThemeStyle]]]] = Field(
        default_factory=dict, description="A dictionary mapping theme parameters to lists of theme colors and styles"
    )
