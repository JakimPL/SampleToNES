import dearpygui.dearpygui as dpg

from sampletones_application.constants.graphs import TAG_THEME_GRAPH_OVERLAY
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class OverlayGraphTheme(Theme):
    tag: str = TAG_THEME_GRAPH_OVERLAY
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GraphsLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvShadeSeries): [
                    ThemeColor(
                        key=dpg.mvPlotCol_Fill,
                        color=layout.colors.waveform_overlay,
                        category=dpg.mvThemeCat_Plots,
                    ),
                ],
            }
        )
