from typing import List, Optional, Tuple

import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.layout.loader import load_layout_config
from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_ORDER_TABLE,
    TAG_SEQUENCER_TRACKER_TABLE,
)
from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.elements.table.selection import TableSelection
from sampletones_application.ui.panels.sequencer.grid.scroll.axis import (
    HorizontalScroll,
    ScrollAxis,
    VerticalScroll,
)
from sampletones_application.ui.panels.sequencer.grid.scroll.band import TravelBand
from sampletones_application.ui.panels.sequencer.grid.scroll.travel import DragTravel
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel, OrderKey
from sampletones_application.ui.panels.sequencer.tracker import CellKey, GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.modifiers import Modifier
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from sampletones_application.view_model.sequencer.region import OrderRegion, TrackerRegion
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName

ROW_COUNT = 64
POSITION_COUNT = 8
ORIGIN_WIDGET = 101
ORIGIN_CELL: CellKey = (2, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
ORIGIN_ENTRY: OrderKey = (None, 1)


@pytest.fixture
def layout_config() -> LayoutConfig:
    source = PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default)
    return load_layout_config(LAYOUT_DIRECTORY, BEHAVIOR_DIRECTORY, source)


@pytest.fixture
def sequencer_layout(layout_config: LayoutConfig) -> SequencerLayout:
    return layout_config.tabs.sequencer


def _resting_travel(axis: ScrollAxis) -> DragTravel:
    """A travel over a grid that was never drawn: stating no band, it carries a drag nowhere."""
    return DragTravel(axis=axis, band=lambda: None, elapsed=lambda: 1.0 / 60.0)


def _hold_modifiers(
    monkeypatch: pytest.MonkeyPatch,
    module: str,
    shift: bool,
) -> None:
    """Holds Shift down for both readers of it: the drag reads the press, the panel the click."""
    modifiers = {Modifier.SHIFT} if shift else set()
    monkeypatch.setattr(
        f"sampletones_application.ui.panels.sequencer.{module}.capture_modifiers",
        lambda: modifiers,
    )
    monkeypatch.setattr(
        "sampletones_application.ui.elements.table.drag.capture_modifiers",
        lambda: modifiers,
    )


def _tracker(
    monkeypatch: pytest.MonkeyPatch,
    reached: Optional[CellKey],
    shift: bool = False,
) -> Tuple[GUISequencerTrackerPanel, List[TrackerInputState]]:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._input_state = TrackerInputState()
    panel._current_row_count = ROW_COUNT
    panel._editable_cells = EditableCells()
    panel._editable_cells.register(ORIGIN_CELL, ORIGIN_WIDGET)
    panel._selection = TableSelection(
        cells=panel._editable_cells,
        cell_at=lambda: panel._cell_at(),
        covered=panel._selected_cells,
    )
    panel._travel = _resting_travel(VerticalScroll(table=TAG_SEQUENCER_TRACKER_TABLE))

    states: List[TrackerInputState] = []
    monkeypatch.setattr(panel, "_apply_state", states.append)
    monkeypatch.setattr(panel, "_cell_at", lambda: reached)
    _hold_modifiers(monkeypatch, "tracker", shift)
    return panel, states


def _order(
    monkeypatch: pytest.MonkeyPatch,
    reached: Optional[OrderKey],
    shift: bool = False,
) -> Tuple[GUISequencerOrderPanel, List[OrderInputState]]:
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    panel._input_state = OrderInputState()
    panel._position_count = POSITION_COUNT
    panel._order = EditableCells()
    panel._order.register(ORIGIN_ENTRY, ORIGIN_WIDGET)
    panel._selection = TableSelection(
        cells=panel._order,
        cell_at=lambda: panel._cell_at(),
        covered=panel._selected_cells,
    )
    panel._travel = _resting_travel(HorizontalScroll(table=TAG_SEQUENCER_ORDER_TABLE))

    states: List[OrderInputState] = []
    monkeypatch.setattr(panel, "_apply_state", states.append)
    monkeypatch.setattr(panel, "_cell_at", lambda: reached)
    _hold_modifiers(monkeypatch, "order", shift)
    return panel, states


def _silence_click(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lets a click run over a grid that was never drawn: the cells it releases hold no widget."""
    monkeypatch.setattr(
        "sampletones_application.ui.elements.table.selection.dpg.set_value",
        lambda widget, value: None,
    )


class TestTrackerDrag:
    """A press carries the selection with the pointer, and a press that stays put stays a click."""

    def test_a_press_alone_selects_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _tracker(monkeypatch, reached=ORIGIN_CELL)

        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states == []

    def test_a_press_held_on_its_own_cell_stays_a_click(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _tracker(monkeypatch, reached=ORIGIN_CELL)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states == []

    def test_a_drag_anchors_at_the_pressed_cell(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reached: CellKey = (5, GeneratorName.TRIANGLE, SubColumn.VOLUME)
        panel, states = _tracker(monkeypatch, reached=reached)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states[-1].region == TrackerRegion(
            first_row=2,
            last_row=5,
            first_slot=4,
            last_slot=11,
        )

    def test_a_plain_drag_replaces_the_selection_already_held(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reached: CellKey = (5, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
        panel, states = _tracker(monkeypatch, reached=reached)
        panel._input_state = TrackerInputState(
            cursor=TrackerCursor(20, GeneratorName.NOISE, SubColumn.VOLUME),
            anchor=TrackerCursor(30, GeneratorName.NOISE, SubColumn.VOLUME),
        )

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states[-1].anchor == TrackerCursor(*ORIGIN_CELL)
        assert states[-1].region == TrackerRegion(
            first_row=2,
            last_row=5,
            first_slot=4,
            last_slot=4,
        )

    def test_a_shift_press_carries_the_selection_already_held(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reached: CellKey = (5, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
        panel, states = _tracker(monkeypatch, reached=reached, shift=True)
        panel._input_state = TrackerInputState(
            cursor=TrackerCursor(9, GeneratorName.PULSE1, SubColumn.TRANSPOSE),
            anchor=TrackerCursor(9, GeneratorName.PULSE2, SubColumn.TRANSPOSE),
        )

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states[-1].anchor == TrackerCursor(9, GeneratorName.PULSE2, SubColumn.TRANSPOSE)

    def test_a_drag_back_to_its_origin_selects_that_cell(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reached: CellKey = (5, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
        panel, states = _tracker(monkeypatch, reached=reached)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        monkeypatch.setattr(panel, "_cell_at", lambda: ORIGIN_CELL)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states[-1].region == TrackerRegion(
            first_row=2,
            last_row=2,
            first_slot=4,
            last_slot=4,
        )

    def test_a_press_on_a_cell_the_cache_forgot_selects_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _tracker(monkeypatch, reached=ORIGIN_CELL)

        panel._on_cell_held(0, ORIGIN_WIDGET + 1)
        panel._on_cell_held(0, ORIGIN_WIDGET + 1)

        assert states == []

    def test_a_new_press_ends_the_gesture_before_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The press starting a gesture ends the one before it, so its click places the cursor."""
        reached: CellKey = (5, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
        panel, states = _tracker(monkeypatch, reached=reached)
        _silence_click(monkeypatch)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_pointer_pressed(0, 0)
        panel._on_cell_clicked(ORIGIN_WIDGET, True, ORIGIN_CELL)

        assert states[-1].cursor == TrackerCursor(*ORIGIN_CELL)
        assert states[-1].region is None

    def test_the_click_ending_a_drag_leaves_the_selection_alone(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A drag returning to its own cell releases there, and that release reports a click."""
        reached: CellKey = (5, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
        panel, states = _tracker(monkeypatch, reached=reached)
        _silence_click(monkeypatch)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        applied = len(states)
        panel._on_cell_clicked(ORIGIN_WIDGET, True, ORIGIN_CELL)

        assert len(states) == applied


class TestTrackerDragHitTest:
    """The row under the pointer is counted from the first row, and clipped to the rows there are."""

    def test_each_row_answers_for_its_own_band(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sequencer_layout: SequencerLayout,
    ) -> None:
        panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        panel._layout = sequencer_layout
        panel._current_row_count = ROW_COUNT
        monkeypatch.setattr(panel, "_row_top", lambda index: 100.0 if index == 0 else None)

        height = sequencer_layout.tracker.row_height
        assert panel._row_at(100.0) == 0
        assert panel._row_at(100.0 + height - 1) == 0
        assert panel._row_at(100.0 + height) == 1
        assert panel._row_at(100.0 + 3 * height + 2) == 3

    def test_a_pointer_past_an_edge_reads_as_the_edge(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sequencer_layout: SequencerLayout,
    ) -> None:
        panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        panel._layout = sequencer_layout
        panel._current_row_count = ROW_COUNT
        monkeypatch.setattr(panel, "_row_top", lambda index: 100.0 if index == 0 else None)

        assert panel._row_at(-500.0) == 0
        assert panel._row_at(100_000.0) == ROW_COUNT - 1

    def test_a_grid_awaiting_its_rows_answers_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sequencer_layout: SequencerLayout,
    ) -> None:
        panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        panel._layout = sequencer_layout
        panel._current_row_count = 0
        monkeypatch.setattr(panel, "_row_top", lambda index: None)

        assert panel._row_at(100.0) is None


class TestTravelBands:
    """Each grid states the band a drag held past an edge travels across, in its own axis."""

    def test_the_tracker_band_runs_from_the_first_row(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sequencer_layout: SequencerLayout,
    ) -> None:
        panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        panel._layout = sequencer_layout
        panel._current_row_count = ROW_COUNT
        monkeypatch.setattr(panel, "_row_top", lambda index: 100.0 if index == 0 else None)

        assert panel._travel_band() == TravelBand(
            first_edge=100.0,
            cell_extent=sequencer_layout.tracker.row_height,
            cell_count=ROW_COUNT,
        )

    def test_a_tracker_awaiting_its_rows_states_no_band(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sequencer_layout: SequencerLayout,
    ) -> None:
        panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        panel._layout = sequencer_layout
        panel._current_row_count = ROW_COUNT
        monkeypatch.setattr(panel, "_row_top", lambda index: None)

        assert panel._travel_band() is None

    def test_an_empty_frame_states_no_band(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sequencer_layout: SequencerLayout,
    ) -> None:
        panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
        panel._layout = sequencer_layout
        panel._current_row_count = 0
        monkeypatch.setattr(panel, "_row_top", lambda index: 100.0)

        assert panel._travel_band() is None

    def test_the_order_band_runs_across_from_the_first_position(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
        panel._position_count = POSITION_COUNT
        monkeypatch.setattr(panel, "_cell_left", lambda position: 40.0 + 25.0 * position)

        assert panel._travel_band() == TravelBand(
            first_edge=40.0,
            cell_extent=25.0,
            cell_count=POSITION_COUNT,
        )

    def test_an_order_of_one_position_states_no_band(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A single position holds every width there is, so nothing states the pitch to travel by."""
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
        panel._position_count = 1
        monkeypatch.setattr(panel, "_cell_left", lambda position: 40.0 if position == 0 else None)

        assert panel._travel_band() is None


class TestOrderDrag:
    """The order table reads a drag the same way, over its channels and positions."""

    def test_a_press_alone_selects_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _order(monkeypatch, reached=ORIGIN_ENTRY)

        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states == []

    def test_a_drag_anchors_at_the_pressed_cell(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reached: OrderKey = (GeneratorName.PULSE2, 4)
        panel, states = _order(monkeypatch, reached=reached)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states[-1].region == OrderRegion(
            first_row=0,
            last_row=2,
            first_position=1,
            last_position=4,
        )

    def test_a_shift_press_carries_the_selection_already_held(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reached: OrderKey = (GeneratorName.PULSE2, 4)
        panel, states = _order(monkeypatch, reached=reached, shift=True)
        panel._input_state = OrderInputState(
            cursor=OrderCursor(GeneratorName.NOISE, 6),
            anchor=OrderCursor(GeneratorName.NOISE, 6),
        )

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert states[-1].anchor == OrderCursor(GeneratorName.NOISE, 6)

    def test_a_new_press_ends_the_gesture_before_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The press starting a gesture ends the one before it, so its click places the cursor."""
        reached: OrderKey = (GeneratorName.PULSE2, 4)
        panel, states = _order(monkeypatch, reached=reached)
        _silence_click(monkeypatch)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_pointer_pressed(0, 0)
        panel._on_cell_clicked(ORIGIN_WIDGET, True, ORIGIN_ENTRY)

        assert states[-1].cursor == OrderCursor(*ORIGIN_ENTRY)
        assert states[-1].region is None

    def test_the_click_ending_a_drag_leaves_the_selection_alone(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reached: OrderKey = (GeneratorName.PULSE2, 4)
        panel, states = _order(monkeypatch, reached=reached)
        _silence_click(monkeypatch)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        applied = len(states)
        panel._on_cell_clicked(ORIGIN_WIDGET, True, ORIGIN_ENTRY)

        assert len(states) == applied
