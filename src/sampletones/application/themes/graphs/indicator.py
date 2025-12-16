import dearpygui.dearpygui as dpg

from ...constants.graphs import (
    COL_WAVEFORM_POSITION_INDICATOR,
    TAG_THEME_GRAPH_INDICATOR,
    VAL_WAVEFORM_POSITION_INDICATOR_THICKNESS,
)
from ..items import ThemeItems
from ..style import ThemeColor, ThemeParameter, ThemeStyle
from ..theme import Theme


class IndicatorGraphTheme(Theme):
    tag: str = TAG_THEME_GRAPH_INDICATOR
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvLineSeries): [
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
