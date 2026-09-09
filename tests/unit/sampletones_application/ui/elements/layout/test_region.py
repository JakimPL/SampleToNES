from typing import Any, Iterator, List, Optional, Tuple
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.paths import PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_LEAD
from sampletones_application.ui.elements.layout.geometry import RowGeometry
from sampletones_application.ui.elements.layout.region import (
    NO_GUTTER,
    NO_SCROLL,
    LeadBuilder,
    WindowedRegion,
)
from sampletones_application.ui.elements.layout.well import well
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
PADDING = 8
GUTTER = 13
MARGIN = 6
NO_MARGIN = 0
LEAD_TAG = compose_tag(REGION_TAG, SUF_LEAD)
HEADING_HEIGHT = 50.0
NO_HEADING = 0.0
FITTING_ROWS = 4
MEASURING_ROWS = 8


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
        gutter=NO_GUTTER,
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


def block_of(height: float, *, lead: float = NO_HEADING) -> Any:
    """Stands in for the rows a frame placed, and for the heading standing above them.

    A block is measured whole, so the heading's own room is part of what a region reads and comes
    out of it again before a row is counted from what is left.
    """

    def measured(item: str, *_args: Any, **_kwargs: Any) -> List[float]:
        return [0.0, lead if item == LEAD_TAG else height]

    return patch.object(dpg, "get_item_rect_size", side_effect=measured)


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
            gutter=NO_GUTTER,
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
            gutter=NO_GUTTER,
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

    def test_a_region_taking_the_height_it_measures_asks_to_be_read_back(
        self,
        unmeasured: WindowedRegion,
    ) -> None:
        """The height a region opens at is not the one it measures, and a move is a move.

        Whatever the region is drawn inside measures it as it stands, so the height it takes to
        read a row by asks for the same further pass a height taken from a reading does.
        """
        draw(unmeasured, 4)

        unmeasured.settle()

        assert unmeasured.settling

    def test_a_region_with_nothing_to_read_comes_to_rest_where_it_stands(
        self,
        unmeasured: WindowedRegion,
    ) -> None:
        """A region drawn where no frame has placed its rows measures nothing, and settles anyway.

        The first pass moves it off the height it opened at, which is a move like any other and
        asks to be read back. The pass that follows finds it standing where it already stood, so a
        region with nothing to measure comes to rest rather than asking on every frame.
        """
        draw(unmeasured, 4)
        unmeasured.settle()

        unmeasured.settle()

        assert not unmeasured.settling


class TestAHeightTheFrameHasYetToShow(BaseTestSuite):
    """A region that takes a new height stands at its old one until the frame after.

    Whatever the region is drawn inside measures it as it stands, so a region reporting itself at
    rest the moment it resizes leaves the one around it holding a scrollbar over content that fits.
    """

    @pytest.fixture
    def sizing(self, dpg_context: None) -> WindowedRegion:
        built = WindowedRegion(
            tag=REGION_TAG,
            geometry=RowGeometry(overscan=OVERSCAN, pitch=PITCH),
            ceiling=CEILING,
            padding=0,
            margin=0,
            gutter=NO_GUTTER,
        )
        with dpg.window(tag=ROOT_TAG):
            built.create(ROOT_TAG)

        return built

    def test_a_region_that_shrank_below_its_ceiling_asks_for_another_pass(
        self,
        sizing: WindowedRegion,
    ) -> None:
        draw(sizing, 500)
        sizing.settle()

        draw(sizing, 2)
        sizing.settle()

        assert sizing.natural
        assert sizing.settling

    def test_a_region_standing_where_it_stood_comes_to_rest(self, sizing: WindowedRegion) -> None:
        draw(sizing, 2)
        sizing.settle()

        sizing.settle()

        assert not sizing.settling


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

    def test_the_room_the_rows_ask_for_counts_the_heading(self, region: WindowedRegion) -> None:
        """Rows that stand inside the region alone outgrow it once a heading stands above them."""
        draw(region, FITTING_ROWS, lead=heading)

        with block_of(NO_HEADING, lead=HEADING_HEIGHT):
            region.settle()

        assert not region.natural

    def test_the_same_rows_without_one_stand_inside_it(self, region: WindowedRegion) -> None:
        """What puts the rows past the ceiling is the heading, so without one they fit."""
        draw(region, FITTING_ROWS, lead=heading)

        with block_of(NO_HEADING, lead=NO_HEADING):
            region.settle()

        assert region.natural

    def test_the_reading_of_a_row_leaves_the_heading_out(self, dpg_context: None) -> None:
        """A block is measured with the heading in it, so a row is counted from what is left."""
        geometry = RowGeometry.unmeasured(overscan=OVERSCAN)
        built = WindowedRegion(
            tag=REGION_TAG,
            geometry=geometry,
            ceiling=CEILING,
            padding=0,
            margin=0,
            gutter=NO_GUTTER,
        )
        with dpg.window(tag=ROOT_TAG):
            built.create(ROOT_TAG)

        drawn = draw(built, MEASURING_ROWS, lead=heading)
        with block_of(drawn[0][1] * PITCH + HEADING_HEIGHT, lead=HEADING_HEIGHT):
            built.settle()

        assert geometry.pitch == PITCH


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

    def test_content_past_the_ceiling_is_held_at_it(self, region: WindowedRegion) -> None:
        """What a region holds is measured rather than counted, since it is more than a run of rows."""
        region.draw_whole(lambda: dpg.add_text("banded", parent=region.body), lead=None, rows=0)

        with block_of(CEILING + PITCH):
            region.settle()

        assert not region.natural
        assert dpg.get_item_configuration(REGION_TAG)["height"] == CEILING
        assert dpg.get_item_configuration(REGION_TAG)["auto_resize_y"] is False

    def test_content_inside_the_ceiling_sizes_the_region_to_itself(self, region: WindowedRegion) -> None:
        """A region held at its ceiling follows what it holds back down once that fits again."""
        region.draw_whole(lambda: dpg.add_text("banded", parent=region.body), lead=None, rows=0)
        with block_of(CEILING + PITCH):
            region.settle()

        with block_of(CEILING - PITCH):
            region.settle()

        assert region.natural
        assert dpg.get_item_configuration(REGION_TAG)["auto_resize_y"] is True
        assert dpg.get_item_configuration(REGION_TAG)["no_scrollbar"] is True


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

    def test_a_region_opening_where_it_already_stands_writes_nothing(self, region: WindowedRegion) -> None:
        """A folder opens at the top by default, which is where the region stands, so no scroll is written."""
        region.opens_at(NO_SCROLL)
        draw(region, 40)

        with patch.object(dpg, "set_y_scroll") as set_y_scroll:
            settled = region.settle()

        set_y_scroll.assert_not_called()
        assert settled is False

    def test_it_is_handed_back_once(self, region: WindowedRegion) -> None:
        """A restored position is where the reader stands, so the next frame writes nothing."""
        region.opens_at(STANDING_OFFSET)
        draw(region, 40)
        with patch.object(dpg, "set_y_scroll"):
            region.settle()

        with patch.object(dpg, "set_y_scroll") as set_y_scroll:
            region.settle()

        set_y_scroll.assert_not_called()


class TestARegionWhoseBodyHasGone(BaseTestSuite):
    """A window closing takes the region's whole subtree down while the pass that settles it is
    still armed, so the region answers for a body that is no longer there."""

    def test_it_asks_for_nothing_more(self, region: WindowedRegion) -> None:
        draw(region, 40)
        dpg.delete_item(ROOT_TAG, children_only=True)

        assert region.settle() is False
        assert region.settling is False

    def test_a_draw_reaching_it_builds_nothing(self, region: WindowedRegion) -> None:
        """Building into a parent that has been freed is what a closed dialog would otherwise do."""
        draw(region, 40)
        dpg.delete_item(ROOT_TAG, children_only=True)

        assert draw(region, 40) == []


class TestTheGutterAScrollbarWillTake(BaseTestSuite):
    """A region holds the scrollbar's room clear until the scrollbar itself takes it.

    A child window's scrollbar comes out of the room its content stands in, so a grid inside a
    region that scrolls would stand narrower than the same grid inside one that fits. Holding the
    room clear while no scrollbar stands keeps the content one width across the moment it starts
    scrolling, which is what lines a folder's columns up with the columns around it.
    """

    @pytest.fixture(name="gutted")
    def gutted_fixture(self, dpg_context: None) -> WindowedRegion:
        built = WindowedRegion(
            tag=REGION_TAG,
            geometry=RowGeometry(overscan=OVERSCAN, pitch=PITCH),
            ceiling=CEILING,
            padding=PADDING,
            margin=0,
            gutter=GUTTER,
        )
        with dpg.window(tag=ROOT_TAG):
            built.create(ROOT_TAG)

        return built

    @staticmethod
    def _inset(region: WindowedRegion) -> int:
        """The room the body holds clear at its right, which a negative width states."""
        return -int(dpg.get_item_configuration(region.body)["width"])

    def test_a_region_standing_whole_holds_the_room_clear(self, gutted: WindowedRegion) -> None:
        draw(gutted, 4)
        gutted.settle()

        assert self._inset(gutted) == PADDING + GUTTER

    def test_a_region_that_scrolls_gives_the_room_up(self, gutted: WindowedRegion) -> None:
        """The scrollbar stands in that room itself, so the body would otherwise pay for it twice."""
        with block_of(PITCH * 500):
            draw(gutted, 500)
            gutted.settle()

        assert self._inset(gutted) == PADDING

    def test_a_region_falling_back_under_its_ceiling_holds_it_again(self, gutted: WindowedRegion) -> None:
        with block_of(PITCH * 500):
            draw(gutted, 500)
            gutted.settle()

        draw(gutted, 4)
        gutted.settle()

        assert self._inset(gutted) == PADDING + GUTTER


class TestTheGapAWellOpens(BaseTestSuite):
    """A well opens a gap above its first row and below its last, or lays its rows flush.

    A well standing on a card of its own opens the gap so its body reads apart from the card's
    edge; one nested inside a list lays its rows flush, since the list's own rhythm carries them.
    """

    @staticmethod
    def _built(dpg_context: None, *, margin: int) -> str:
        with dpg.window(tag=ROOT_TAG):
            body = well(ROOT_TAG, REGION_TAG, padding=PADDING, margin=margin, width=-PADDING)

        return body

    def test_a_well_asked_for_a_gap_lays_a_spacer_either_side(self, dpg_context: None) -> None:
        body = self._built(dpg_context, margin=MARGIN)

        laid = dpg.get_item_children(REGION_TAG, 1)

        assert len(laid) == 3
        assert laid[1] == dpg.get_alias_id(body)
        assert dpg.get_item_configuration(laid[0])["height"] == MARGIN
        assert dpg.get_item_configuration(laid[2])["height"] == MARGIN

    def test_a_well_asked_for_none_opens_its_rows_where_it_opens(self, dpg_context: None) -> None:
        body = self._built(dpg_context, margin=NO_MARGIN)

        laid = dpg.get_item_children(REGION_TAG, 1)

        assert laid == [dpg.get_alias_id(body)]
