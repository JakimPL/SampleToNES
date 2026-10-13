from typing import Final, Iterator, List, Tuple

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import SUF_OWNERSHIP_RUN
from sampletones_application.ui.elements.graphs.ownership import OwnershipRuns, traced
from sampletones_application.utils.palette.colors.literal import LiteralColor
from sampletones_application.view_model.shared.ownership import OwnershipRunViewModel
from sampletones_shared.types.application import ColorRGBA

RECORDING_COLORS: Final[Tuple[ColorRGBA, ...]] = ((200, 80, 40, 255), (80, 160, 220, 255))
AUTHORED_COLOR: Final[ColorRGBA] = (180, 140, 240, 255)
REST_COLOR: Final[ColorRGBA] = (40, 40, 48, 255)
LEFT_OUT_FRACTION: Final[float] = 0.4
FRAME_SPAN: Final[float] = 2.0
BAND: Final[Tuple[float, float]] = (0.1, 0.9)
Y_AXIS: Final[str] = "ownership_test_axis"
FIRST: Final[int] = 0
SECOND: Final[int] = 1


def _runs(*entries: Tuple[int, int, int, bool]) -> Tuple[OwnershipRunViewModel, ...]:
    return tuple(
        OwnershipRunViewModel(start_frame=start, end_frame=end, stem_id=stem_id, heard=heard)
        for start, end, stem_id, heard in entries
    )


def _series(stem_id: int) -> str:
    return compose_tag(Y_AXIS, SUF_OWNERSHIP_RUN, str(stem_id))


@pytest.fixture
def stem_colors() -> StemColors:
    return StemColors(
        recordings=tuple(LiteralColor(value) for value in RECORDING_COLORS),
        authored=LiteralColor(AUTHORED_COLOR),
        rest=LiteralColor(REST_COLOR),
        left_out_fraction=LEFT_OUT_FRACTION,
    )


@pytest.fixture
def axis() -> Iterator[str]:
    """A plot's y axis in a context of the case's own, which the painter draws into."""
    dpg.create_context()
    with dpg.window():
        with dpg.plot():
            dpg.add_plot_axis(dpg.mvXAxis)
            dpg.add_plot_axis(dpg.mvYAxis, tag=Y_AXIS)

    yield Y_AXIS
    dpg.destroy_context()


class TestTracingStretches:
    """A series rises at the start of each stretch and falls at its end, so it fills the stretches alone."""

    def test_each_stretch_is_four_points_rising_and_falling(self) -> None:
        positions, lower, upper = traced(((0, 4), (8, 12)), FRAME_SPAN, BAND)

        assert positions == [0.0, 0.0, 8.0, 8.0, 16.0, 16.0, 24.0, 24.0]
        assert lower == [BAND[0]] * 8
        assert upper == [BAND[0], BAND[1], BAND[1], BAND[0]] * 2

    def test_no_stretch_traces_nothing(self) -> None:
        assert traced((), FRAME_SPAN, BAND) == ([], [], [])


class TestPaintingALane:
    """A lane is painted as one series per recording, and a repaint touches a series only where it changed."""

    def test_each_recording_is_one_series(self, stem_colors: StemColors, axis: str) -> None:
        painter = OwnershipRuns(stem_colors)

        painter.paint(
            axis,
            _runs((0, 4, FIRST, True), (4, 8, SECOND, True), (8, 12, FIRST, True)),
            frame_span=FRAME_SPAN,
            band=BAND,
        )

        assert dpg.does_item_exist(_series(FIRST))
        assert dpg.does_item_exist(_series(SECOND))
        assert dpg.get_value(_series(FIRST))[0] == [0.0, 0.0, 8.0, 8.0, 16.0, 16.0, 24.0, 24.0]

    def test_a_recording_heard_no_more_keeps_its_series_and_changes_its_theme(
        self,
        stem_colors: StemColors,
        axis: str,
    ) -> None:
        painter = OwnershipRuns(stem_colors)
        painter.paint(axis, _runs((0, 4, FIRST, True), (4, 8, SECOND, True)), frame_span=FRAME_SPAN, band=BAND)
        first = dpg.get_alias_id(_series(FIRST))
        heard_themes = (dpg.get_item_theme(_series(FIRST)), dpg.get_item_theme(_series(SECOND)))

        painter.paint(axis, _runs((0, 4, FIRST, False), (4, 8, SECOND, True)), frame_span=FRAME_SPAN, band=BAND)

        assert dpg.get_alias_id(_series(FIRST)) == first
        assert dpg.get_item_theme(_series(FIRST)) != heard_themes[0]
        assert dpg.get_item_theme(_series(SECOND)) == heard_themes[1]

    def test_moved_stretches_are_traced_again(self, stem_colors: StemColors, axis: str) -> None:
        painter = OwnershipRuns(stem_colors)
        painter.paint(axis, _runs((0, 4, FIRST, True)), frame_span=FRAME_SPAN, band=BAND)

        painter.paint(axis, _runs((0, 6, FIRST, True)), frame_span=FRAME_SPAN, band=BAND)

        assert dpg.get_value(_series(FIRST))[0] == [0.0, 0.0, 12.0, 12.0]

    def test_a_recording_leaving_the_lane_leaves_the_axis(self, stem_colors: StemColors, axis: str) -> None:
        painter = OwnershipRuns(stem_colors)
        painter.paint(axis, _runs((0, 4, FIRST, True), (4, 8, SECOND, True)), frame_span=FRAME_SPAN, band=BAND)

        painter.paint(axis, _runs((0, 8, FIRST, True)), frame_span=FRAME_SPAN, band=BAND)

        assert dpg.does_item_exist(_series(FIRST))
        assert not dpg.does_item_exist(_series(SECOND))

    def test_an_empty_lane_leaves_nothing_painted(self, stem_colors: StemColors, axis: str) -> None:
        painter = OwnershipRuns(stem_colors)
        painter.paint(axis, _runs((0, 4, FIRST, True)), frame_span=FRAME_SPAN, band=BAND)

        painter.paint(axis, (), frame_span=FRAME_SPAN, band=BAND)

        assert not dpg.does_item_exist(_series(FIRST))

    def test_a_series_taken_off_the_axis_elsewhere_is_drawn_again(self, stem_colors: StemColors, axis: str) -> None:
        painter = OwnershipRuns(stem_colors)
        painter.paint(axis, _runs((0, 4, FIRST, True)), frame_span=FRAME_SPAN, band=BAND)
        dpg.delete_item(_series(FIRST))

        painter.paint(axis, _runs((0, 4, FIRST, True)), frame_span=FRAME_SPAN, band=BAND)

        assert dpg.does_item_exist(_series(FIRST))
