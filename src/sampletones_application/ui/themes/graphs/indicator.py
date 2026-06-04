import dearpygui.dearpygui as dpg

from sampletones_application.constants.graphs import TAG_THEME_GRAPH_INDICATOR
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
)
from sampletones_application.ui.themes.theme import Theme


class IndicatorGraphTheme(Theme):
    tag: str = TAG_THEME_GRAPH_INDICATOR
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GraphsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvInfLineSeries): [
                    ThemeColor(
                        key=dpg.mvPlotCol_Line,
                        color=layout.colors.waveform_position_indicator,
                        category=dpg.mvThemeCat_Plots,
                    ),
                    ThemeStyle(
                        key=dpg.mvPlotStyleVar_LineWeight,
                        x=layout.waveform.position_indicator_thickness,
                        category=dpg.mvThemeCat_Plots,
                    ),
                ],
            }
        )
