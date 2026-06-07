import dearpygui.dearpygui as dpg

from sampletones_application.constants.sequencer import TAG_SEQUENCER_INSTRUMENTS_THEME_ROW
from sampletones_application.layout.sequencer import SequencerLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class InstrumentsRowTheme(Theme):
    tag: str = TAG_SEQUENCER_INSTRUMENTS_THEME_ROW
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, sequencer: SequencerLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTable): [
                    ThemeColor(key=dpg.mvThemeCol_HeaderHovered, color=sequencer.colors.pattern_highlight),
                    ThemeColor(key=dpg.mvThemeCol_HeaderActive, color=(0, 0, 0, 0)),
                ],
            }
        )
