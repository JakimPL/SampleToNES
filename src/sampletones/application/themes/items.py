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


class ThemeParameter(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    item_type: int = Field(..., description="The Dear PyGui theme component identifier")
    enabled_state: bool = Field(default=True, description="The enabled state for the theme component")

    __hash__ = object.__hash__  # type: ignore[assignment]


class ThemeItems(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    items: Dict[ThemeParameter, List[Union[ThemeColor, ThemeStyle]]] = Field(
        default_factory=dict, description="A dictionary mapping theme parameters to lists of theme colors and styles"
    )
