import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.palette.binding import COLOR_ARGUMENT
from sampletones_application.utils.gui.palette.palette import PaletteBindings
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.application import Sender


def dpg_set_palette_color(
    item: Sender,
    color: BaseColor,
    *,
    argument: str = COLOR_ARGUMENT,
) -> None:
    """Colours an item so it follows the palette, in place of passing ``color=`` to DearPyGui.

    Args:
        item: Item to colour.
        color: Token the colour is read from, kept for the next palette in place.
        argument: Name of the item's colour argument, for an item that carries more than one.
    """
    PaletteBindings.bind(
        item,
        color,
        argument=argument,
    )


def dpg_add_palette_theme_color(
    key: int,
    color: BaseColor,
    *,
    category: int = dpg.mvThemeCat_Core,
) -> Sender:
    """Adds a theme colour that follows the palette, inside an open theme component.

    Args:
        key: Theme colour constant the value fills, such as ``dpg.mvThemeCol_Text``.
        color: Token the colour is read from, kept for the next palette in place.
        category: Theme category the constant belongs to.

    Returns:
        Sender: The theme colour item, which repaints every widget bound to the theme.
    """
    item: Sender = dpg.add_theme_color(
        key,
        color.rgba,
        category=category,
    )
    PaletteBindings.bind_theme_color(item, color)
    return item
