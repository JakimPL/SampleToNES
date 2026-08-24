from typing import Final, Generator, List
from unittest.mock import MagicMock

import dearpygui.dearpygui as dpg
import numpy as np
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LANG_EN,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
    THEME_DIRECTORY,
)
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_shared.types.application import ColorRGBA

PULSE: Final[ColorRGBA] = (240, 146, 86, 255)
TRIANGLE: Final[ColorRGBA] = (140, 193, 237, 255)
NOISE: Final[ColorRGBA] = (187, 184, 194, 255)

VOICE_NAME: Final[str] = "lead"
AUDIO: Final[np.ndarray] = np.zeros(8)


@pytest.fixture
def graph() -> Generator[GUIWaveformGraph, None, None]:
    """A waveform graph on a live DearPyGui context, which is what holds the series themes."""
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    layout: LayoutConfig = load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)
    dpg.create_context()
    try:
        setup_themes(THEME_DIRECTORY, source)
        FontRegistry.setup(layout.fonts)
        FontRegistry.register_fonts()
        with dpg.window(tag="root"):
            yield GUIWaveformGraph(
                tag="waveform",
                parent="root",
                layout=layout.graphs,
                language_manager=LanguageManager(LANG_EN),
                status_bar=MagicMock(),
            )
    finally:
        dpg.destroy_context()


def _drawn_color(graph: GUIWaveformGraph) -> ColorRGBA:
    """The color DearPyGui holds on the one series the graph is showing."""
    layer = next(iter(graph.layers.values()))
    theme = dpg.get_item_theme(graph._series_tag(layer.name))
    component = dpg.get_item_children(theme, 1)[0]
    return tuple(round(value) for value in dpg.get_value(dpg.get_item_children(component, 1)[0]))


class TestASeriesTakesTheColorItWasGiven:
    def test_a_voice_reloaded_in_another_color_is_drawn_in_that_color(
        self,
        graph: GUIWaveformGraph,
    ) -> None:
        """A layer keeps its name across loads, so the theme follows the color, not the name."""
        drawn: List[ColorRGBA] = []
        for color in (PULSE, TRIANGLE, NOISE):
            graph.load_voice_waveform(AUDIO, name=VOICE_NAME, color=LiteralColor(color))
            drawn.append(_drawn_color(graph))

        assert drawn == [PULSE, TRIANGLE, NOISE]

    def test_a_color_shown_twice_is_built_once(self, graph: GUIWaveformGraph) -> None:
        for color in (PULSE, TRIANGLE, PULSE):
            graph.load_voice_waveform(AUDIO, name=VOICE_NAME, color=LiteralColor(color))

        assert len(graph._series_themes) == 2
