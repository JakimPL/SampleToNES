import dearpygui.dearpygui as dpg

from ...constants.reconstructions import (
    TAG_THEME_TABLE_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
    VAL_TABLE_CELL_PADDING_RECONSTRUCTIONS_DETAILS_INITIAL_PITCH,
)
from ..items import ThemeItems
from ..style import ThemeParameter, ThemeStyle
from ..theme import Theme


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
