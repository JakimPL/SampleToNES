from typing import Any, Iterator, List, Optional, Tuple
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.paths import PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.ui.elements.layout.geometry import RowGeometry
from sampletones_application.ui.elements.layout.region import LeadBuilder, WindowedRegion
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.setup import setup_themes
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from tests.suite.base import BaseTestSuite

ROOT_TAG = "test_root"
REGION_TAG = "test.region"
PITCH = 20.0
OVERSCAN = 2
CEILING = 100
HEADING_TEXT = "channels"
STANDING_OFFSET = 300.0


@pytest.fixture
def dpg_context() -> Iterator[None]:
    """Stands up the context and themes a recessed region binds while it draws."""
    dpg.create_context()
    setup_themes(THEME_DIRECTORY, PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default))
    try:
        yield
    finally:
        ThemeRegistry.clear()
        dpg.destroy_context()


@pytest.fixture
def region(dpg_context: None) -> WindowedRegion:
    """A region whose reading of a row is already taken, as a list that has drawn rows leaves it."""
    built = WindowedRegion(
        tag=REGION_TAG,
        geometry=RowGeometry(overscan=OVERSCAN, pitch=PITCH),
        ceiling=CEILING,
        padding=0,
        margin=0,
    )
    with dpg.window(tag=ROOT_TAG):
        built.create(ROOT_TAG)

    return built


def heading(parent: str) -> None:
    """A heading of the kind a list stands above its rows."""
    dpg.add_text(HEADING_TEXT, parent=parent)


def draw(region: WindowedRegion, total: int, *, lead: Optional[LeadBuilder] = None) -> List[Tuple[int, int]]:
    """Draw a list of ``total`` rows, reporting the slice the region asked to be built."""
    asked: List[Tuple[int, int]] = []

    def build(start: int, count: int) -> None:
        asked.append((start, count))
        for index in range(start, start + count):
            dpg.add_text(f"row {index}", parent=region.body)

    region.draw(total, build, lead=lead)
    return asked


def block_of(height: float) -> Any:
    """Stands in for the rows a frame placed, which is what a reading of a row is taken from."""
    return patch.object(dpg, "get_item_rect_size", return_value=[0, height])


def reserves(region: WindowedRegion) -> Tuple[int, int]:
    """The room standing above and below the rows the region drew."""
    spacers = [
        child
        for child in dpg.get_item_children(region.body, 1)
        if dpg.get_item_type(child) == "mvAppItemType::mvSpacer"
    ]
    return (
        int(dpg.get_item_configuration(spacers[0])["height"]),
        int(dpg.get_item_configuration(spacers[-1])["height"]),
    )


class TestAShortList(BaseTestSuite):
    """A list the region can show whole is built whole, with no room reserved either side."""

    def test_every_row_is_built(self, region: WindowedRegion) -> None:
        assert draw(region, 4) == [(0, 4)]

    def test_nothing_is_reserved(self, region: WindowedRegion) -> None:
        draw(region, 4)
        assert reserves(region) == (0, 0)

    def test_the_window_names_the_whole_list(self, region: WindowedRegion) -> None:
        draw(region, 4)
        assert region.window == (0, 4)


class TestALongList(BaseTestSuite):
    """A list outgrowing the region is built a slice at a time, the rest standing as room."""

    def test_only_the_slice_is_built(self, region: WindowedRegion) -> None:
        assert draw(region, 500) == [(0, 10)]

    def test_the_rows_still_to_come_are_reserved(self, region: WindowedRegion) -> None:
        draw(region, 500)
        above, below = reserves(region)
        assert above == 0
        assert below == int((500 - 10) * PITCH)

    def test_the_reserves_and_the_slice_span_the_whole_list(self, region: WindowedRegion) -> None:
        draw(region, 500)
        above, below = reserves(region)
        _, count = region.window
        assert above + int(count * PITCH) + below == int(500 * PITCH)


class TestAnUnmeasuredRegion(BaseTestSuite):
    """A region with no reading of a row yet builds a first slice at its natural height and
    reserves nothing, which is the run of rows a reading is then taken from."""

    @pytest.fixture
    def unmeasured(self, dpg_context: None) -> WindowedRegion:
        built = WindowedRegion(
            tag=REGION_TAG,
            geometry=RowGeometry.unmeasured(overscan=OVERSCAN),
            ceiling=CEILING,
            padding=0,
            margin=0,
        )
        with dpg.window(tag=ROOT_TAG):
            built.create(ROOT_TAG)

        return built

    def test_it_builds_a_bounded_slice_of_a_long_list(self, unmeasured: WindowedRegion) -> None:
        asked = draw(unmeasured, 5_000)
        assert asked[0][0] == 0
        assert asked[0][1] < 5_000

    def test_it_reserves_nothing_while_it_has_no_reading(self, unmeasured: WindowedRegion) -> None:
        draw(unmeasured, 5_000)
        assert reserves(unmeasured) == (0, 0)

    def test_a_short_list_is_still_built_whole(self, unmeasured: WindowedRegion) -> None:
        assert draw(unmeasured, 4) == [(0, 4)]


class TestAReadingTheHeightHasYetToFollow(BaseTestSuite):
    """A region reads what a row takes from the rows it drew, which is a frame after it was sized.

    The reading is what says how tall the whole list stands, so a region holding it is standing at
    a height decided before it knew: :attr:`settling` is what asks for the pass that puts it right,
    and without one a long list stands as tall as every row it drew.
    """

    @pytest.fixture
    def unmeasured(self, dpg_context: None) -> WindowedRegion:
        built = WindowedRegion(
            tag=REGION_TAG,
            geometry=RowGeometry.unmeasured(overscan=OVERSCAN),
            ceiling=CEILING,
            padding=0,
            margin=0,
        )
        with dpg.window(tag=ROOT_TAG):
            built.create(ROOT_TAG)

        return built

    def test_a_reading_asks_for_the_pass_that_holds_the_region_to_it(self, unmeasured: WindowedRegion) -> None:
        drawn = draw(unmeasured, 500)
        with block_of(drawn[0][1] * PITCH):
            unmeasured.settle()

        assert unmeasured.settling

    def test_that_pass_holds_the_region_to_its_ceiling(self, unmeasured: WindowedRegion) -> None:
        drawn = draw(unmeasured, 500)
        with block_of(drawn[0][1] * PITCH):
            unmeasured.settle()

        assert unmeasured.settle()
        assert not unmeasured.natural
        assert draw(unmeasured, 500)[0][1] < drawn[0][1]

    def test_it_comes_to_rest_once_the_height_follows_the_reading(self, unmeasured: WindowedRegion) -> None:
        """A list the region shows whole holds nothing back, so the reading is the last thing due."""
        drawn = draw(unmeasured, 4)
        with block_of(drawn[0][1] * PITCH):
            unmeasured.settle()

        unmeasured.settle()

        assert not unmeasured.settling

    def test_a_region_with_nothing_to_read_asks_for_nothing(self, unmeasured: WindowedRegion) -> None:
        """A region drawn where no frame has placed its rows measures nothing, and waits."""
        draw(unmeasured, 4)
        unmeasured.settle()

        assert not unmeasured.settling


class TestRedrawing(BaseTestSuite):
    """A region drawn again replaces what it held, so its rows stand once however often it is
    rebuilt."""

    def test_a_second_draw_builds_the_slice_once(self, region: WindowedRegion) -> None:
        draw(region, 500)
        draw(region, 500)
        _, count = region.window
        assert len(dpg.get_item_children(region.body, 1)) == count + 2

    def test_a_shorter_list_reserves_less(self, region: WindowedRegion) -> None:
        draw(region, 500)
        draw(region, 20)
        _, below = reserves(region)
        assert below == int((20 - 10) * PITCH)


class TestALead(BaseTestSuite):
    """A heading standing above the rows is built with them and scrolls with them."""

    def test_the_heading_stands_before_the_rows(self, region: WindowedRegion) -> None:
        draw(region, 4, lead=heading)
        first = dpg.get_item_children(region.body, 1)[0]

        assert dpg.get_item_type(first) == "mvAppItemType::mvGroup"

    def test_the_rows_are_reserved_around_as_they_are_without_one(self, region: WindowedRegion) -> None:
        draw(region, 500, lead=heading)

        assert reserves(region) == (0, int((500 - 10) * PITCH))

    def test_a_region_drawn_again_holds_one_heading(self, region: WindowedRegion) -> None:
        draw(region, 4, lead=heading)
        draw(region, 4, lead=heading)
        groups = [
            child
            for child in dpg.get_item_children(region.body, 1)
            if dpg.get_item_type(child) == "mvAppItemType::mvGroup"
        ]

        assert len(groups) == 1


class TestAWholeDraw(BaseTestSuite):
    """Content that is more than a run of rows is built entire, and the region holds it to its
    ceiling from there on."""

    def test_everything_it_is_given_is_built(self, region: WindowedRegion) -> None:
        region.draw_whole(
            lambda: [dpg.add_text(f"row {index}", parent=region.body) for index in range(30)], lead=None, rows=30
        )

        assert len(dpg.get_item_children(region.body, 1)) == 30

    def test_it_holds_back_no_rows(self, region: WindowedRegion) -> None:
        region.draw_whole(lambda: dpg.add_text("banded", parent=region.body), lead=None, rows=0)

        assert not region.windowing

    def test_it_carries_its_heading_too(self, region: WindowedRegion) -> None:
        region.draw_whole(lambda: dpg.add_text("banded", parent=region.body), lead=heading, rows=0)
        first = dpg.get_item_children(region.body, 1)[0]

        assert dpg.get_item_type(first) == "mvAppItemType::mvGroup"


class TestWhereTheReaderStands(BaseTestSuite):
    """A region redrawn as the reader scrolls leaves the scroll where they put it, and one built
    in place of another opens where that one stood.

    The rows a region shows are replaced a frame after the wheel asked for them, by which time the
    reader has scrolled on. A position written back then lands against the wheel and takes them
    somewhere they never scrolled, which asks for the rows to be replaced again — a region that
    never settles while a hand is on the wheel.
    """

    def test_a_draw_writes_no_scroll(self, region: WindowedRegion) -> None:
        with patch.object(dpg, "set_y_scroll") as set_y_scroll:
            draw(region, 40)

        set_y_scroll.assert_not_called()

    def test_the_window_follows_where_the_reader_scrolled_to(self, region: WindowedRegion) -> None:
        draw(region, 40)
        region.settle()

        with patch.object(dpg, "get_y_scroll", return_value=STANDING_OFFSET):
            asked = draw(region, 40)

        assert asked[0][0] > 0

    def test_a_redraw_the_scroll_asked_for_hands_nothing_back(self, region: WindowedRegion) -> None:
        """By the frame the rows land the reader has scrolled on, so the region leaves them there."""
        draw(region, 40)
        region.settle()
        with patch.object(dpg, "get_y_scroll", return_value=STANDING_OFFSET):
            draw(region, 40)

        with (
            patch.object(dpg, "get_y_scroll", return_value=STANDING_OFFSET + PITCH),
            patch.object(dpg, "set_y_scroll") as set_y_scroll,
        ):
            region.settle()

        set_y_scroll.assert_not_called()


class TestARegionOpeningInPlaceOfAnother(BaseTestSuite):
    """A region built where one a rebuild took down stood opens on the rows that one showed."""

    def test_its_window_opens_where_the_one_before_it_stood(self, region: WindowedRegion) -> None:
        region.opens_at(STANDING_OFFSET)

        asked = draw(region, 40)

        assert asked[0][0] > 0

    def test_the_reader_is_put_back_once_the_rows_are_placed(self, region: WindowedRegion) -> None:
        region.opens_at(STANDING_OFFSET)
        draw(region, 40)

        with patch.object(dpg, "set_y_scroll") as set_y_scroll:
            region.settle()

        set_y_scroll.assert_called_once_with(REGION_TAG, STANDING_OFFSET)

    def test_it_is_handed_back_once(self, region: WindowedRegion) -> None:
        """A restored position is where the reader stands, so the next frame writes nothing."""
        region.opens_at(STANDING_OFFSET)
        draw(region, 40)
        with patch.object(dpg, "set_y_scroll"):
            region.settle()

        with patch.object(dpg, "set_y_scroll") as set_y_scroll:
            region.settle()

        set_y_scroll.assert_not_called()
