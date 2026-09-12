from typing import Final

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import SUF_TEXT
from sampletones_application.ui.elements.stems.tags import StemsTags

CLICKED: Final[str] = "mvAppItemType::mvClickedHandler"
DOUBLE_CLICKED: Final[str] = "mvAppItemType::mvDoubleClickedHandler"
HOVERED: Final[str] = "mvAppItemType::mvHoverHandler"


def handler_of(registry: str, kind: str) -> int:
    """The handler answering one kind of gesture in a registry, found by what it is.

    A registry holds its handlers in the order they were added, so reading one by its position
    names a different gesture as soon as another is registered beside it.
    """
    for handler in dpg.get_item_children(registry, 1):
        if dpg.get_item_info(handler)["type"] == kind:
            return int(handler)

    raise AssertionError(f"{registry} registers no {kind}")


def click_row_name(tags: StemsTags, key: str, *, kind: str, button: int) -> None:
    """Land a mouse gesture on one row's name the way DearPyGui reports one."""
    name_tag = tags.row(key, SUF_TEXT)
    callback = dpg.get_item_callback(handler_of(tags.handlers(SUF_TEXT), kind))
    callback(name_tag, (button, dpg.get_alias_id(name_tag)))
