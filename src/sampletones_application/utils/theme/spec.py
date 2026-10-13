from __future__ import annotations

from typing import Annotated, Final, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from sampletones_application.utils.palette.colors.written import WrittenColor

BASE_THEME_NAME: Final[str] = "default"
EVERY_ITEM_TYPE_NAME: Final[str] = "All"
CORE_CATEGORY: Final[str] = "Core"


class ThemeColorEntrySpec(BaseModel, frozen=True):
    type: Literal["color"]
    key: str
    value: WrittenColor
    category: str = CORE_CATEGORY


class ThemeStyleEntrySpec(BaseModel, frozen=True):
    type: Literal["style"]
    key: str
    x: float
    y: float = -1.0
    category: str = CORE_CATEGORY


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

    @property
    def parent(self) -> Optional[str]:
        """The theme this one composes on top of.

        A theme inherits from its explicit ``extends`` when given, and otherwise from the base
        theme, so every theme carries the shared base's complete component set and states only
        its own overrides. The base theme itself stands alone. This makes inheritance the
        default: a bound item theme always resolves to the global base plus its overrides, so
        every color it omits keeps the base's value.
        """
        if self.extends is not None:
            return self.extends

        if self.name != BASE_THEME_NAME:
            return BASE_THEME_NAME

        return None
