import dearpygui.dearpygui as dpg

from sampletones_application.constants.sequencer import TAG_THEME_TABLE_PATTERN
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
)
from sampletones_application.ui.themes.theme import Theme


class PatternTableTheme(Theme):
    tag: str = TAG_THEME_TABLE_PATTERN
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, general: GeneralLayout, sequencer: SequencerLayout) -> None:
        t = general.tables
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTable): [
                    ThemeStyle(
                        key=dpg.mvStyleVar_CellPadding,
                        x=t.cell_padding[0],
                        y=t.cell_padding[1],
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_HeaderHovered,
                        color=sequencer.colors.pattern_highlight,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_HeaderActive,
                        color=(0, 0, 0, 0),
                    ),
                ],
            }
        )
