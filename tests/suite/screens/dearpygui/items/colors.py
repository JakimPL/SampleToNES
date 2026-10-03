from typing import Dict, Final, List, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.items.types import Item

THEME_COLOR_TYPE: Final[str] = "mvAppItemType::mvThemeColor"
COLOR_ATTRIBUTES: Final[Tuple[str, ...]] = ("color", "fill")
THEME_COLOR_VALUE: Final[str] = "value"
THEME_TARGET: Final[str] = "target"
THEME_CATEGORY: Final[str] = "category"
COLOR_PARTS: Final[int] = 4
COLOR_DIGITS: Final[int] = 4
COLOR_STEPS: Final[float] = 255.0


def read_theme(item: Item) -> Optional[str]:
    """The tag of the theme bound to ``item``, if one is. Runs on the render thread."""
    theme = dpg.get_item_info(item)["theme"]
    if theme is None:
        return None

    return str(dpg.get_item_alias(theme))


def read_theme_colors(theme: Item) -> Tuple[Tuple[float, ...], ...]:
    """The colors every theme color under ``theme`` holds, in the order they were added. Runs on the render thread."""
    colors: List[Tuple[float, ...]] = []
    for component in dpg.get_item_children(theme, 1):
        for color in dpg.get_item_children(component, 1):
            colors.append(tuple(float(part) for part in dpg.get_value(color)))

    return tuple(colors)


def read_held_colors() -> Dict[str, Tuple[float, ...]]:
    """Every color DearPyGui holds for the interface, keyed by the item and the attribute holding it. Runs on the
    render thread.

    A theme color holds its value whether or not anything wearing it is drawn; an item holds its own color and fill
    while it stands shown. Every value reads as fractions of the full step, rounded, so a color given in whole steps
    reads the same from either side.
    """
    held: Dict[str, Tuple[float, ...]] = {}
    for item in dpg.get_all_items():
        if dpg.get_item_info(item)["type"] == THEME_COLOR_TYPE:
            held[f"{item}:{THEME_COLOR_VALUE}"] = _theme_color(item)
            continue

        if not dpg.is_item_shown(item):
            continue

        configuration = dpg.get_item_configuration(item)
        for attribute in COLOR_ATTRIBUTES:
            value = configuration.get(attribute)
            if _is_color(value):
                held[f"{item}:{attribute}"] = rounded_color(value)

    return held


def read_theme_text_color(theme: Item) -> Optional[Tuple[float, ...]]:
    """The text color ``theme`` sets, if it sets one. Runs on the render thread."""
    for component in dpg.get_item_children(theme, 1):
        for color in dpg.get_item_children(component, 1):
            configuration = dpg.get_item_configuration(color)
            if (
                configuration.get(THEME_TARGET) == dpg.mvThemeCol_Text
                and configuration.get(THEME_CATEGORY) == dpg.mvThemeCat_Core
            ):
                return _theme_color(color)

    return None


def rounded_color(value: Sequence[float]) -> Tuple[float, ...]:
    """A color's parts, rounded so a color read from DearPyGui and one stated in whole steps compare equal."""
    return tuple(round(float(part), COLOR_DIGITS) for part in value)


def _theme_color(item: Item) -> Tuple[float, ...]:
    """The color a theme color item holds, as a fraction of the full step like an item's own color reads.

    DearPyGui answers a theme color in whole steps and an item's color in fractions of one.
    """
    return rounded_color(tuple(float(part) / COLOR_STEPS for part in dpg.get_value(item)))


def _is_color(value: object) -> bool:
    """Whether a configuration value is a color DearPyGui holds, which an unset one, read as negatives, is not."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == COLOR_PARTS
        and all(isinstance(part, (int, float)) and part >= 0 for part in value)
    )
