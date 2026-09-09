from typing import Any, Dict, Iterator, List, Tuple
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import BEHAVIOR_DIRECTORY, LAYOUT_DIRECTORY, PALETTES_DIRECTORY
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.stems.columns import COLUMN_BORDER, StemsColumns
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_core.constants.enums import ChannelName
from tests.suite.base import BaseTestSuite

ROOT_TAG = "test_root"
TABLE_TAG = "test_table"
GLYPH = "▸"
GLYPH_WIDTH = 9.0
GLYPH_SIZE = [GLYPH_WIDTH, 20.0]
CHANNELS: Tuple[ChannelName, ...] = (ChannelName.PULSE1, ChannelName.TRIANGLE)


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def dpg_context(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands up the context and the faces a measurement is taken in."""
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    try:
        yield
    finally:
        dpg.destroy_context()


def columns(
    layout_config: LayoutConfig,
    *,
    folders: bool,
    master: bool = False,
    bends: bool = False,
) -> StemsColumns:
    """The grid a list of gathered recordings declares."""
    return StemsColumns(
        layout=layout_config.general.stems,
        channels=CHANNELS,
        master=master,
        removable=True,
        bends=bends,
        folders=folders,
    )


def measured(size: object) -> object:
    """What DearPyGui answers a text measurement with, which needs a drawn frame to be a size."""
    return patch.object(dpg, "get_text_size", return_value=size)


class TestWhereARowWithoutAMarkerOpens(BaseTestSuite):
    """A folder's marker glyph stands in the middle of the room the marker is given, and a row
    carrying no marker opens its name there, so the names read as one column."""

    def test_the_name_opens_where_the_glyph_stands(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        stems = layout_config.general.stems

        with measured(GLYPH_SIZE):
            indent = columns(layout_config, folders=True).marker_indent(GLYPH, Font.ICON)

        assert indent == (stems.twisty_width - int(GLYPH_WIDTH)) // 2

    def test_a_grid_holding_no_folder_opens_its_names_at_the_edge(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """No marker leads any row there, so there is nothing for a name to line up with."""
        with measured(GLYPH_SIZE):
            indent = columns(layout_config, folders=False).marker_indent(GLYPH, Font.ICON)

        assert indent == 0

    def test_a_glyph_no_frame_has_measured_yet_opens_at_the_edge(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A measurement waits on a drawn frame, and the next reading of the list settles it."""
        with measured(None):
            indent = columns(layout_config, folders=True).marker_indent(GLYPH, Font.ICON)

        assert indent == 0


class TestWhereABoxStands(BaseTestSuite):
    """Every box stands in the middle of the column it belongs to, whichever column that is."""

    def test_a_channel_box_is_centered_in_its_column(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        """One box stands in a column the width the layout gives a channel standing on its own."""
        stems = layout_config.general.stems

        indent = columns(layout_config, folders=True).box_indent(ChannelName.PULSE1)

        assert indent == (stems.channel_solo_width - stems.channel_box_width) // 2

    def test_a_channel_carrying_its_bend_centers_both_boxes_together(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        """A tone channel's cell holds the channel and the bend on it, in a column of its own width."""
        stems = layout_config.general.stems

        indent = columns(layout_config, folders=True, bends=True).box_indent(ChannelName.PULSE1)

        assert indent == (stems.channel_column_width - 2 * stems.channel_box_width) // 2

    def test_a_channel_taking_no_bend_keeps_the_one_box(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        """A bend moves a note within its divider, so noise holds the first slot alone."""
        stems = layout_config.general.stems

        indent = columns(layout_config, folders=True, bends=True).box_indent(ChannelName.NOISE)

        assert indent == (stems.channel_column_width - stems.channel_box_width) // 2

    def test_the_box_beside_a_row_is_centered_in_its_own_column(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        """The master column is narrower than a channel's, so it takes an indent of its own."""
        stems = layout_config.general.stems

        indent = columns(layout_config, folders=True, master=True).master_indent

        assert indent == (stems.master_column_width - stems.channel_box_width) // 2

    def test_a_box_wider_than_its_column_opens_at_the_edge(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        grid = columns(layout_config, folders=True)
        wide = grid.layout.model_copy(update={"master_column_width": 1})

        indent = StemsColumns(
            layout=wide,
            channels=CHANNELS,
            master=True,
            removable=True,
            bends=False,
            folders=True,
        ).master_indent

        assert indent == 0


class TestTheRoomAFolderSpends(BaseTestSuite):
    """A folder draws its recordings inside a region of its own, and the room that region spends
    at its right is held clear across every table outside it, so the columns stand in one grid."""

    def test_a_grid_holding_folders_holds_the_room_clear(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        """A region insets its body by the well's padding and holds a scrollbar's width beside it."""
        stems = layout_config.general.stems

        reserve = columns(layout_config, folders=True).reserve

        assert reserve == stems.well_padding + stems.scrollbar_width

    def test_a_grid_holding_none_spends_nothing(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        assert columns(layout_config, folders=False).reserve == 0

    def test_the_reserve_column_comes_out_the_width_of_the_room(
        self,
        layout_config: LayoutConfig,
    ) -> None:
        """A column takes its own width plus the padding either side and the rule beside it."""
        stems = layout_config.general.stems
        grid = columns(layout_config, folders=True)

        assert grid.reserve_width == grid.reserve - 2 * stems.cell_padding - COLUMN_BORDER


class TestTheColumnsAGridDeclares(BaseTestSuite):
    """A grid declares its columns in one order at one set of widths, which is what stands every
    table of a stems list — and the settings card's single row — in the same grid."""

    @staticmethod
    def _declared(grid: StemsColumns) -> List[Dict[str, Any]]:
        """The columns one table comes out holding, as a reader would measure them."""
        with dpg.window(tag=ROOT_TAG):
            with dpg.table(tag=TABLE_TAG):
                grid.declare()

        return [dpg.get_item_configuration(column) for column in dpg.get_item_children(TABLE_TAG, 0)]

    def test_a_grid_holding_folders_ends_on_the_reserved_strip(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """The strip stands where a folder's region spends its room, so the columns line up."""
        grid = columns(layout_config, folders=True)

        declared = self._declared(grid)

        assert declared[-1]["init_width_or_weight"] == grid.reserve_width
        assert len(declared) == len(CHANNELS) + 3

    def test_a_grid_holding_none_ends_on_the_removal_column(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A card drawing one row opens no region, so a strip held clear there would be negative."""
        stems = layout_config.general.stems
        grid = columns(layout_config, folders=False)

        declared = self._declared(grid)

        assert grid.reserve_width < 0
        assert declared[-1]["init_width_or_weight"] == stems.remove_button_width
        assert len(declared) == len(CHANNELS) + 2

    def test_the_name_column_is_the_one_that_stretches(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        """A wider card spends its room on the recordings rather than on the boxes beside them."""
        declared = self._declared(columns(layout_config, folders=True, master=True))

        assert [column["width_stretch"] for column in declared].count(True) == 1
        assert declared[1]["width_stretch"] is True

    def test_each_channel_takes_the_width_its_boxes_ask_for(
        self,
        dpg_context: None,
        layout_config: LayoutConfig,
    ) -> None:
        stems = layout_config.general.stems
        grid = columns(layout_config, folders=True, bends=True)

        declared = self._declared(grid)

        assert [column["init_width_or_weight"] for column in declared[1 : 1 + len(CHANNELS)]] == [
            stems.channel_column_width
        ] * len(CHANNELS)
