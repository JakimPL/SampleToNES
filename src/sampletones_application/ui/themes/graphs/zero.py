import dearpygui.dearpygui as dpg

from sampletones_application.constants.graphs import TAG_GLOBAL_GRAPH_THEME_ZERO_LINE
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
)
from sampletones_application.ui.themes.theme import Theme


class ZeroLineGraphTheme(Theme):
    tag: str = TAG_GLOBAL_GRAPH_THEME_ZERO_LINE
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GraphsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvInfLineSeries): [
                    ThemeColor(
                        key=dpg.mvPlotCol_Line,
                        color=layout.colors.bar_plot_zero_line,
                        category=dpg.mvThemeCat_Plots,
                    ),
                    ThemeStyle(
                        key=dpg.mvPlotStyleVar_LineWeight,
                        x=layout.bar_plot.zero_line_thickness,
                        category=dpg.mvThemeCat_Plots,
                    ),
                ],
            }
        )
