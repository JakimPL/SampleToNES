from typing import Dict, List, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.ui.themes.style import ThemeParameter, ThemeValue

ThemeValues = Union[List[ThemeValue]]
ThemeItemsDictionary = Dict[ThemeParameter, ThemeValues]
ThemeDictionary = Dict[Tuple[ThemeParameter, int], ThemeValue]


class ThemeItems(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    items: ThemeItemsDictionary = Field(
        default_factory=dict,
        description="A dictionary mapping theme parameters to lists of theme colors and styles",
    )
