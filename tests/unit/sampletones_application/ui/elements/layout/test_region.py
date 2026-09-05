from typing import Iterator, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.paths import PALETTES_DIRECTORY, THEME_DIRECTORY
from sampletones_application.ui.elements.layout.geometry import RowGeometry
from sampletones_application.ui.elements.layout.region import WindowedRegion
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


def draw(region: WindowedRegion, total: int) -> List[Tuple[int, int]]:
    """Draw a list of ``total`` rows, reporting the slice the region asked to be built."""
    asked: List[Tuple[int, int]] = []

    def build(start: int, count: int) -> None:
        asked.append((start, count))
        for index in range(start, start + count):
            dpg.add_text(f"row {index}", parent=region.body)

    region.draw(total, build)
    return asked


def reserves(region: WindowedRegion) -> Tuple[int, int]:
    """The room standing above and below the rows the region drew."""
    children = dpg.get_item_children(region.body, 1)
    return (
        int(dpg.get_item_configuration(children[0])["height"]),
        int(dpg.get_item_configuration(children[-1])["height"]),
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
