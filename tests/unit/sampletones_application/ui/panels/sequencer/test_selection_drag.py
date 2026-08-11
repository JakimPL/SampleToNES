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
from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
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


def _hold_modifiers(
    monkeypatch: pytest.MonkeyPatch,
    module: str,
    shift: bool,
) -> None:
    monkeypatch.setattr(
        f"sampletones_application.ui.panels.sequencer.{module}.capture_modifiers",
        lambda: {Modifier.SHIFT} if shift else set(),
    )


def _tracker(
    monkeypatch: pytest.MonkeyPatch,
    reached: Optional[CellKey],
    shift: bool = False,
) -> Tuple[GUISequencerTrackerPanel, List[TrackerInputState]]:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._input_state = TrackerInputState()
    panel._current_row_count = ROW_COUNT
    panel._drag = None
    panel._editable_cells = EditableCells()
    panel._editable_cells.register(ORIGIN_CELL, ORIGIN_WIDGET)

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
    panel._drag = None
    panel._order = EditableCells()
    panel._order.register(ORIGIN_ENTRY, ORIGIN_WIDGET)

    states: List[OrderInputState] = []
    monkeypatch.setattr(panel, "_apply_state", states.append)
    monkeypatch.setattr(panel, "_cell_at", lambda: reached)
    _hold_modifiers(monkeypatch, "order", shift)
    return panel, states


class TestEditableCellKeys:
    """A cell cache answers from both sides, because a handler reports the widget it fired for."""

    def test_a_registered_widget_reads_back_as_its_key(self) -> None:
        cells: EditableCells[CellKey] = EditableCells()
        cells.register(ORIGIN_CELL, ORIGIN_WIDGET)

        assert cells.key(ORIGIN_WIDGET) == ORIGIN_CELL
        assert cells.widget(ORIGIN_CELL) == ORIGIN_WIDGET

    def test_a_rebuild_drops_both_directions(self) -> None:
        cells: EditableCells[CellKey] = EditableCells()
        cells.register(ORIGIN_CELL, ORIGIN_WIDGET)
        cells.reset({})

        assert cells.key(ORIGIN_WIDGET) is None
        assert cells.widget(ORIGIN_CELL) is None

    def test_an_unknown_widget_names_no_cell(self) -> None:
        cells: EditableCells[CellKey] = EditableCells()

        assert cells.key(ORIGIN_WIDGET) is None


class TestTrackerDrag:
    """A press carries the selection with the pointer, and a press that stays put stays a click."""

    def test_a_press_alone_selects_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _tracker(monkeypatch, reached=ORIGIN_CELL)

        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert panel._drag is not None
        assert panel._drag.origin == ORIGIN_CELL
        assert panel._drag.moved is False
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

        assert panel._drag is not None
        assert panel._drag.moved is True
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

    def test_a_press_on_a_cell_the_cache_forgot_starts_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _tracker(monkeypatch, reached=ORIGIN_CELL)

        panel._on_cell_held(0, ORIGIN_WIDGET + 1)

        assert panel._drag is None
        assert states == []

    def test_a_new_press_ends_the_gesture_before_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, _ = _tracker(monkeypatch, reached=ORIGIN_CELL)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_pointer_pressed(0, 0)

        assert panel._drag is None

    def test_the_click_ending_a_drag_leaves_the_selection_alone(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A drag returning to its own cell releases there, and that release reports a click."""
        reached: CellKey = (5, GeneratorName.PULSE1, SubColumn.TRANSPOSE)
        panel, states = _tracker(monkeypatch, reached=reached)
        panel._selection = frozenset({ORIGIN_CELL})
        monkeypatch.setattr(panel, "_repaint_selection", lambda: None)
        monkeypatch.setattr(
            "sampletones_application.ui.panels.sequencer.tracker.dpg.set_value",
            lambda widget, value: None,
        )

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        applied = len(states)
        panel._on_cell_clicked(ORIGIN_WIDGET, True, ORIGIN_CELL)

        assert len(states) == applied
        assert panel._drag is None


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


class TestOrderDrag:
    """The order table reads a drag the same way, over its channels and positions."""

    def test_a_press_alone_selects_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel, states = _order(monkeypatch, reached=ORIGIN_ENTRY)

        panel._on_cell_held(0, ORIGIN_WIDGET)

        assert panel._drag is not None
        assert panel._drag.origin == ORIGIN_ENTRY
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
        panel, _ = _order(monkeypatch, reached=ORIGIN_ENTRY)

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_pointer_pressed(0, 0)

        assert panel._drag is None

    def test_the_click_ending_a_drag_leaves_the_selection_alone(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reached: OrderKey = (GeneratorName.PULSE2, 4)
        panel, states = _order(monkeypatch, reached=reached)
        panel._selection = frozenset({ORIGIN_ENTRY})
        monkeypatch.setattr(panel, "_repaint_selection", lambda: None)
        monkeypatch.setattr(
            "sampletones_application.ui.panels.sequencer.order.dpg.set_value",
            lambda widget, value: None,
        )

        panel._on_cell_held(0, ORIGIN_WIDGET)
        panel._on_cell_held(0, ORIGIN_WIDGET)
        applied = len(states)
        panel._on_cell_clicked(ORIGIN_WIDGET, True, ORIGIN_ENTRY)

        assert len(states) == applied
        assert panel._drag is None
