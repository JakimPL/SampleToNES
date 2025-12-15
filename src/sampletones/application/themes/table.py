import dearpygui.dearpygui as dpg

from ..constants.general import (
    TAG_THEME_TABLE,
    VAL_TABLE_CELL_PADDING,
    VAL_TABLE_FRAME_ROUNDING,
)
from ..constants.reconstructions import (
    TAG_THEME_TABLE_RECONSTRUCTION_DETAILS_INITIAL_PITCH,
    VAL_TABLE_CELL_PADDING_RECONSTRUCTION_DETAILS_INITIAL_PITCH,
)
from .items import ThemeItems, ThemeParameter, ThemeStyle
from .theme import Theme


class TableTheme(Theme):
    tag: str = TAG_THEME_TABLE
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                ThemeStyle(key=dpg.mvStyleVar_CellPadding, x=VAL_TABLE_CELL_PADDING[0], y=VAL_TABLE_CELL_PADDING[1]),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_TABLE_FRAME_ROUNDING),
            ],
        }
    )


class InitialPitchTableTheme(Theme):
    tag: str = TAG_THEME_TABLE_RECONSTRUCTION_DETAILS_INITIAL_PITCH

    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable): [
                ThemeStyle(
                    key=dpg.mvStyleVar_CellPadding,
                    x=VAL_TABLE_CELL_PADDING_RECONSTRUCTION_DETAILS_INITIAL_PITCH[0],
                    y=VAL_TABLE_CELL_PADDING_RECONSTRUCTION_DETAILS_INITIAL_PITCH[1],
                ),
            ],
        }
    )
