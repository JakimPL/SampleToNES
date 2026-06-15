import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_TABLE
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class TableTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_TABLE
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        tables = layout.tables
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                    ThemeStyle(
                        key=dpg.mvStyleVar_CellPadding,
                        x=tables.cell_padding[0],
                        y=tables.cell_padding[1],
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_FrameRounding,
                        x=tables.frame_rounding,
                    ),
                ],
            }
        )
