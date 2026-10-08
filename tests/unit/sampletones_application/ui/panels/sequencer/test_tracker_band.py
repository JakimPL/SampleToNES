from types import SimpleNamespace
from typing import Dict, Final, List, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic
from sampletones_application.tags.sequencer import TAG_SEQUENCER_TRACKER_GROUP, TAG_SEQUENCER_TRACKER_WINDOW
from sampletones_application.ui.panels.sequencer.tracker import panel as tracker
from sampletones_application.ui.panels.sequencer.tracker.band import UNMEASURED_BAND, TrackerBand, TrackerRows
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_application.view_model.sequencer.tracker import NO_REACH, SequencerTrackerViewModel

ROW_HEIGHT: Final[float] = 29.0
HEADER_HEIGHT: Final[float] = 30.0
WINDOW_TOP: Final[float] = 100.0
HEADER_LABEL: Final[str] = "header_label"
FRAME_ROWS: Final[int] = 4
SHOWN_FRAME: Final[int] = 0


class Geometry:
    """The rectangles DearPyGui reports for the grid's window, the group it opens in and the header."""

    def __init__(self) -> None:
        self.band_rows: float = 7.0
        self.header_height: float = HEADER_HEIGHT

    def rect_size(self, item: str) -> Tuple[float, float]:
        sizes: Dict[str, Tuple[float, float]] = {
            TAG_SEQUENCER_TRACKER_WINDOW: (800.0, self.header_height + self.band_rows * ROW_HEIGHT),
            HEADER_LABEL: (30.0, self.header_height),
        }
        return sizes[item]

    def rect_min(self, item: str) -> Tuple[float, float]:
        tops: Dict[str, Tuple[float, float]] = {
            TAG_SEQUENCER_TRACKER_GROUP: (0.0, WINDOW_TOP),
            HEADER_LABEL: (0.0, WINDOW_TOP),
        }
        return tops[item]


@pytest.fixture
def geometry(monkeypatch: pytest.MonkeyPatch) -> Geometry:
    instance = Geometry()
    monkeypatch.setattr(tracker.dpg, "does_item_exist", lambda _item: True)
    monkeypatch.setattr(tracker.dpg, "get_item_rect_size", instance.rect_size)
    monkeypatch.setattr(tracker.dpg, "get_item_rect_min", instance.rect_min)
    return instance


@pytest.fixture
def reported() -> List[int]:
    return []


@pytest.fixture
def panel(reported: List[int]) -> GUISequencerTrackerPanel:
    """A panel that has raised its header, with the grid's band still unmeasured."""
    instance = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    instance._layout = SimpleNamespace(tracker=SimpleNamespace(row_height=ROW_HEIGHT))
    instance._header_label = HEADER_LABEL
    instance._band = TrackerBand(height=UNMEASURED_BAND, row_height=ROW_HEIGHT)
    instance._rows_layout = TrackerRows(reach=NO_REACH, frame_rows=FRAME_ROWS)
    instance.on_reach_changed = reported.append
    return instance


def _grid() -> SequencerTrackerViewModel:
    """The grid of a new project's only frame, :data:`FRAME_ROWS` rows tall."""
    controller = ProjectController(ProjectManager())
    controller.set_rows_per_pattern(FRAME_ROWS)
    return SequencerTrackerLogic(controller).build_grid()


class TestMeasuringTheBand:
    """The band is what the window holds below the header, and a new reach is reported once."""

    @pytest.mark.usefixtures("geometry")
    def test_a_measured_band_reports_the_rows_above_its_center(
        self,
        panel: GUISequencerTrackerPanel,
        reported: List[int],
    ) -> None:
        panel._measure_band()

        assert reported == [3]
        assert panel._band.height == pytest.approx(7.0 * ROW_HEIGHT)

    @pytest.mark.usefixtures("geometry")
    def test_the_same_reach_is_reported_once(self, panel: GUISequencerTrackerPanel, reported: List[int]) -> None:
        panel._measure_band()
        panel._measure_band()

        assert reported == [3]

    def test_a_taller_band_reports_its_new_reach(
        self,
        panel: GUISequencerTrackerPanel,
        reported: List[int],
        geometry: Geometry,
    ) -> None:
        panel._measure_band()
        geometry.band_rows = 11.0
        panel._measure_band()

        assert reported == [3, 5]

    def test_a_grid_awaiting_its_layout_reports_nothing(
        self,
        panel: GUISequencerTrackerPanel,
        reported: List[int],
        geometry: Geometry,
    ) -> None:
        geometry.header_height = 0.0

        panel._measure_band()

        assert reported == []

    def test_a_grid_without_its_header_reports_nothing(
        self,
        panel: GUISequencerTrackerPanel,
        reported: List[int],
    ) -> None:
        panel._header_label = None

        panel._measure_band()

        assert reported == []


class TestTheReachShapesTheTable:
    """A grid arriving under a new reach is built again, and one under the same reach is filled in place."""

    @pytest.fixture
    def rebuilt(self, panel: GUISequencerTrackerPanel, monkeypatch: pytest.MonkeyPatch) -> List[TrackerRows]:
        layouts: List[TrackerRows] = []
        monkeypatch.setattr(
            panel,
            "_rebuild_table",
            lambda _view_model, layout, _values, _kinds: layouts.append(layout),
        )
        panel._displayed_frame = SHOWN_FRAME
        panel._context = MagicMock()
        panel._editable_cells = MagicMock()
        panel._cell_kinds = {}
        monkeypatch.setattr(panel, "_reconcile_cell_kinds", lambda _kinds: None)
        monkeypatch.setattr(panel, "_paint_context", lambda: None)
        return layouts

    def test_a_new_reach_builds_the_rows_either_side(
        self,
        panel: GUISequencerTrackerPanel,
        rebuilt: List[TrackerRows],
    ) -> None:
        panel._band = TrackerBand(height=7.0 * ROW_HEIGHT, row_height=ROW_HEIGHT)

        panel.update_tracker(_grid())

        assert rebuilt == [TrackerRows(reach=3, frame_rows=FRAME_ROWS)]

    def test_the_same_reach_fills_the_rows_in_place(
        self,
        panel: GUISequencerTrackerPanel,
        rebuilt: List[TrackerRows],
    ) -> None:
        grid = _grid()

        panel.update_tracker(grid)

        assert rebuilt == []
        panel._context.fill.assert_called_once_with(grid.lead, grid.trail)
