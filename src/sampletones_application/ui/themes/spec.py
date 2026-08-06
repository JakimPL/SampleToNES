from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from sampletones_application.utils.palette.color import PaletteColor


class ThemeColorEntrySpec(BaseModel, frozen=True):
    type: Literal["color"]
    key: str
    value: PaletteColor
    category: str = "Core"


class ThemeStyleEntrySpec(BaseModel, frozen=True):
    type: Literal["style"]
    key: str
    x: float
    y: float = -1.0
    category: str = "Core"


ThemeEntrySpec = Annotated[
    Union[ThemeColorEntrySpec, ThemeStyleEntrySpec],
    Field(discriminator="type"),
]


class ThemeComponentSpec(BaseModel, frozen=True):
    item_type: str
    enabled: bool = True
    entries: List[ThemeEntrySpec]


class ThemeSpec(BaseModel, frozen=True):
    name: str
    tag: str
    extends: Optional[str] = None
    components: List[ThemeComponentSpec]
