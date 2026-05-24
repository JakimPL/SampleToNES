import dearpygui.dearpygui as dpg

from ...constants.graphs import (
    COL_BAR_PLOT_ZERO_LINE,
    TAG_THEME_GRAPH_ZERO_LINE,
    VAL_BAR_PLOT_ZERO_LINE_THICKNESS,
)
from ..items import ThemeItems
from ..style import ThemeColor, ThemeParameter, ThemeStyle
from ..theme import Theme


class ZeroLineGraphTheme(Theme):
    tag: str = TAG_THEME_GRAPH_ZERO_LINE
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvInfLineSeries): [
                ThemeColor(
                    key=dpg.mvPlotCol_Line,
                    color=COL_BAR_PLOT_ZERO_LINE,
                    category=dpg.mvThemeCat_Plots,
                ),
                ThemeStyle(
                    key=dpg.mvPlotStyleVar_LineWeight,
                    x=VAL_BAR_PLOT_ZERO_LINE_THICKNESS,
                    category=dpg.mvThemeCat_Plots,
                ),
            ],
        }
    )
