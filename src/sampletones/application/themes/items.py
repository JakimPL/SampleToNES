from typing import Dict, List, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from .style import ThemeColor, ThemeParameter, ThemeStyle

ThemeValue = Union[List[ThemeColor], List[ThemeStyle], List[Union[ThemeColor, ThemeStyle]]]
ThemeItemsDictionary = Dict[ThemeParameter, ThemeValue]
ThemeDictionary = Dict[Tuple[ThemeParameter, int], Union[ThemeColor, ThemeStyle]]


class ThemeItems(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    items: ThemeItemsDictionary = Field(
        default_factory=dict,
        description="A dictionary mapping theme parameters to lists of theme colors and styles",
    )
