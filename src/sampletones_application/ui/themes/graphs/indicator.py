import dearpygui.dearpygui as dpg

from sampletones_application.constants.graphs import (
    COL_WAVEFORM_POSITION_INDICATOR,
    TAG_THEME_GRAPH_INDICATOR,
    VAL_WAVEFORM_POSITION_INDICATOR_THICKNESS,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class IndicatorGraphTheme(Theme):
    tag: str = TAG_THEME_GRAPH_INDICATOR
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvInfLineSeries): [
                ThemeColor(
                    key=dpg.mvPlotCol_Line,
                    color=COL_WAVEFORM_POSITION_INDICATOR,
                    category=dpg.mvThemeCat_Plots,
                ),
                ThemeStyle(
                    key=dpg.mvPlotStyleVar_LineWeight,
                    x=VAL_WAVEFORM_POSITION_INDICATOR_THICKNESS,
                    category=dpg.mvThemeCat_Plots,
                ),
            ],
        }
    )
