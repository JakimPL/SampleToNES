import dearpygui.dearpygui as dpg

from ...constants.graphs import COL_WAVEFORM_OVERLAY, TAG_THEME_GRAPH_OVERLAY
from ..items import ThemeColor, ThemeItems, ThemeParameter
from ..theme import Theme


class OverlayGraphTheme(Theme):
    tag: str = TAG_THEME_GRAPH_OVERLAY
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvShadeSeries): [
                ThemeColor(
                    dpg.mvPlotCol_Fill,
                    COL_WAVEFORM_OVERLAY,
                    category=dpg.mvThemeCat_Plots,
                ),
            ],
        }
    )
