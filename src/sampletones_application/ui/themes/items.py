from typing import Dict, List, NamedTuple, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_application.ui.themes.style import ThemeParameter, ThemeValue

ThemeValues = Union[List[ThemeValue]]
ThemeItemsDictionary = Dict[ThemeParameter, ThemeValues]
ThemeDictionary = Dict[Tuple[ThemeParameter, int, bool], ThemeValue]


class ThemeEntryKey(NamedTuple):
    """Merge identity of one theme colour or style entry.

    Entries sharing a key target the same slot, so inheritance resolution lets a
    child theme's entry override its parent's, and the disabled mirror can address
    the disabled counterpart of an enabled slot directly. ``is_style`` separates the
    colour and style enum families, whose integer keys overlap, so a style and a
    colour sharing an item type and integer occupy distinct slots.
    """

    item_type: int
    enabled: bool
    key: int
    category: int
    is_style: bool


class ResolvedThemeEntry(NamedTuple):
    """A theme entry in runtime form: the component it renders under and its value."""

    parameter: ThemeParameter
    value: ThemeValue


ThemeEntries = Dict[ThemeEntryKey, ResolvedThemeEntry]


class ThemeItems(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    items: ThemeItemsDictionary = Field(
        default_factory=dict,
        description="A dictionary mapping theme parameters to lists of theme colors and styles",
    )
