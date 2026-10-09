from typing import Generator, List, Tuple
from unittest.mock import MagicMock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.context import channel_letter
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
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs import waveform as waveform_module
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_core.constants.enums import ChannelName

LANGUAGE_MANAGER = LanguageManager(LANG_EN)


@pytest.fixture(name="layout")
def layout_fixture() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture(name="graph")
def graph_fixture(layout: LayoutConfig) -> Generator[GUIWaveformGraph, None, None]:
    """A waveform graph on a live DearPyGui context, which is what holds the lane rows."""
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
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
                channel_colors=layout.general.colors.channels,
                language_manager=LANGUAGE_MANAGER,
                status_bar=MagicMock(),
            )
    finally:
        dpg.destroy_context()


class TestTheRowsTheLanesAreDrawnIn:
    """Each channel keeps a row of its own beneath the waveform, so a lane carries its letter."""

    def test_every_channel_keeps_a_row(self, graph: GUIWaveformGraph) -> None:
        assert set(graph.lane_plot_tags) == set(ChannelName.items())
        assert all(dpg.does_item_exist(plot_tag) for plot_tag in graph.lane_plot_tags.values())

    def test_a_row_carries_an_axis_of_its_own(self, graph: GUIWaveformGraph) -> None:
        assert all(dpg.does_item_exist(axis_tag) for axis_tag in graph.lane_y_axis_tags.values())
        assert len(set(graph.lane_y_axis_tags.values())) == len(ChannelName.items())

    def test_the_rows_stand_closed_until_a_lane_asks_for_room(self, graph: GUIWaveformGraph) -> None:
        assert dpg.get_item_configuration(graph.subplots_tag)["height"] == graph.height

    def test_a_channel_with_a_lane_takes_the_room_it_asks_for(self, graph: GUIWaveformGraph) -> None:
        graph.set_lane_heights({ChannelName.PULSE1: 11, ChannelName.TRIANGLE: 11})

        assert dpg.get_item_configuration(graph.subplots_tag)["height"] == graph.height + 22

    def test_a_channel_without_a_lane_keeps_no_room(self, graph: GUIWaveformGraph) -> None:
        graph.set_lane_heights({ChannelName.PULSE1: 11, ChannelName.TRIANGLE: 11})
        graph.set_lane_heights({ChannelName.PULSE1: 11})

        assert dpg.get_item_configuration(graph.subplots_tag)["height"] == graph.height + 11

    def test_the_waveform_keeps_its_own_height_whatever_the_lanes_take(self, graph: GUIWaveformGraph) -> None:
        graph.set_lane_heights({channel_name: 11 for channel_name in ChannelName.items()})

        ratios = dpg.get_item_configuration(graph.subplots_tag)["row_ratios"]

        assert ratios[0] == float(graph.height)
        assert ratios[1:] == [11.0] * len(ChannelName.items())


class TestTheFaceALaneIsMarkedIn:
    """A lane one bar high prints its letter in the smallest face, so the letter stands within it."""

    def test_every_lane_takes_the_tiny_face(self, graph: GUIWaveformGraph) -> None:
        tiny = FontRegistry.get_tag(Font.REGULAR_TINY)

        assert all(dpg.get_item_font(plot_tag) == tiny for plot_tag in graph.lane_plot_tags.values())

    def test_the_letter_stands_shorter_than_the_lane_it_marks(self, layout: LayoutConfig) -> None:
        """A letter taller than its lane would run into the lane above, so the face stays under it."""
        assert FontRegistry.get_size(Font.REGULAR_TINY) <= layout.graphs.ribbon.lane_height


class TestTheLetterFollowsWhetherTheLaneStands:
    """A closed lane keeps a sliver of height, so its letter is cleared rather than left to crowd it."""

    @staticmethod
    def _ticks(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, Tuple[Tuple[str, float], ...]]]:
        calls: List[Tuple[str, Tuple[Tuple[str, float], ...]]] = []
        monkeypatch.setattr(waveform_module.dpg, "set_axis_ticks", lambda tag, ticks: calls.append((tag, ticks)))
        return calls

    def test_a_channel_gaining_a_lane_is_marked_with_its_letter(
        self,
        graph: GUIWaveformGraph,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = self._ticks(monkeypatch)

        graph.set_lane_heights({ChannelName.PULSE1: 11})

        letter = channel_letter(LANGUAGE_MANAGER, ChannelName.PULSE1)
        assert (graph.lane_y_axis_tags[ChannelName.PULSE1], ((letter, 0.5),)) in calls

    def test_a_channel_without_a_lane_is_cleared(
        self,
        graph: GUIWaveformGraph,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls = self._ticks(monkeypatch)

        graph.set_lane_heights({ChannelName.PULSE1: 11})

        assert (graph.lane_y_axis_tags[ChannelName.PULSE2], ()) in calls

    def test_a_lane_closed_after_standing_open_loses_its_letter(
        self,
        graph: GUIWaveformGraph,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph.set_lane_heights({ChannelName.PULSE1: 11})
        calls = self._ticks(monkeypatch)

        graph.set_lane_heights({})

        assert (graph.lane_y_axis_tags[ChannelName.PULSE1], ()) in calls
