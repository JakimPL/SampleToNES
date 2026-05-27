import dearpygui.dearpygui as dpg

from sampletones_application.constants.reconstructions import (
    TAG_THEME_TABLE_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
    VAL_TABLE_CELL_PADDING_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class InitialPitchTableTheme(Theme):
    tag: str = TAG_THEME_TABLE_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH

    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable): [
                ThemeStyle(
                    key=dpg.mvStyleVar_CellPadding,
                    x=VAL_TABLE_CELL_PADDING_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH[0],
                    y=VAL_TABLE_CELL_PADDING_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH[1],
                ),
            ],
        }
    )
