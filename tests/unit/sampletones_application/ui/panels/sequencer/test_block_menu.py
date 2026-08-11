from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer import order as order_module
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from tests.suite.shortcuts import shipped_source

CLICKED_ROW = 4
CLICKED_POSITION = 2
ROW_COUNT = 64
POSITION_COUNT = 8

COPY_ITEM = 0
CUT_ITEM = 1
PASTE_ITEM = 2
DELETE_ITEM = 3

PULSE1_ROW = CHANNEL_AXIS.index(GeneratorName.PULSE1)


@dataclass
class MenuItem:
    """One item as it was registered, which is the whole of what a reader sees and clicks."""

    label: str
    enabled: bool
    callback: Callable[[], None]


@dataclass
class Gestures:
    """What each block hook was handed when its menu item fired."""

    copied: List[Any] = field(default_factory=list)
    cut: List[Any] = field(default_factory=list)
    deleted: List[Any] = field(default_factory=list)
    pasted: List[Any] = field(default_factory=list)


class _MenuRecorder:
    """Captures the items a builder registers, in the order it registers them."""

    def __init__(self) -> None:
        self.items: List[MenuItem] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(
            MenuItem(
                label=kwargs["label"],
                enabled=kwargs.get("enabled", True),
                callback=kwargs["callback"],
            )
        )
        return 0


def _labels(panel: Any) -> None:
    panel._lbl_context_copy = "Copy"
    panel._lbl_context_cut = "Cut"
    panel._lbl_context_paste = "Paste"
    panel._lbl_context_delete = "Delete"


def _tracker_panel(
    gestures: Gestures,
    *,
    can_paste: bool = True,
) -> tracker_module.GUISequencerTrackerPanel:
    """A tracker panel whose menu builder can run with no DearPyGui context behind it."""
    panel = tracker_module.GUISequencerTrackerPanel.__new__(tracker_module.GUISequencerTrackerPanel)
    _labels(panel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState()
    panel.on_copy_block = gestures.copied.append
    panel.on_cut_block = gestures.cut.append
    panel.on_delete_block = gestures.deleted.append
    panel.on_paste_block = gestures.pasted.append
    panel.can_paste_block = lambda: can_paste
    return panel


def _order_panel(
    gestures: Gestures,
    *,
    can_paste: bool = True,
) -> order_module.GUISequencerOrderPanel:
    """An order panel whose menu builder can run with no DearPyGui context behind it."""
    panel = order_module.GUISequencerOrderPanel.__new__(order_module.GUISequencerOrderPanel)
    _labels(panel)
    panel._shortcuts = shipped_source()
    panel._input_state = OrderInputState()
    panel.on_copy_block = gestures.copied.append
    panel.on_cut_block = gestures.cut.append
    panel.on_delete_block = gestures.deleted.append
    panel.on_paste_block = gestures.pasted.append
    panel.can_paste_block = lambda: can_paste
    return panel


@pytest.fixture
def tracker_recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    recorder = _MenuRecorder()
    monkeypatch.setattr(tracker_module.dpg, "add_menu_item", recorder.add_menu_item)
    return recorder


@pytest.fixture
def order_recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    recorder = _MenuRecorder()
    monkeypatch.setattr(order_module.dpg, "add_menu_item", recorder.add_menu_item)
    return recorder


def _selected_tracker_state() -> TrackerInputState:
    """A selection running from the clicked row down two rows, over Pulse 1's whole cell."""
    state = TrackerInputState(cursor=TrackerCursor(CLICKED_ROW, GeneratorName.PULSE1, SubColumn.INSTRUMENT))
    return state.extend_row(2, ROW_COUNT).extend_slot(2)


def _selected_order_state() -> OrderInputState:
    """A selection running from the clicked position across two positions of Pulse 1's row."""
    state = OrderInputState(cursor=OrderCursor(GeneratorName.PULSE1, CLICKED_POSITION))
    return state.extend_position(2, POSITION_COUNT)


class TestTrackerMenuTarget:
    def test_a_menu_raised_inside_a_selection_acts_on_the_whole_of_it(self) -> None:
        panel = _tracker_panel(Gestures())
        panel._input_state = _selected_tracker_state()

        region = panel._menu_region(
            CLICKED_ROW + 1,
            GeneratorName.PULSE1,
            SubColumn.TRANSPOSE,
        )

        assert region == panel._input_state.region

    def test_a_menu_raised_outside_a_selection_acts_on_the_clicked_cell(self) -> None:
        panel = _tracker_panel(Gestures())
        panel._input_state = _selected_tracker_state()

        region = panel._menu_region(
            CLICKED_ROW,
            GeneratorName.TRIANGLE,
            SubColumn.VOLUME,
        )

        assert region == TrackerRegion(
            first_row=CLICKED_ROW,
            last_row=CLICKED_ROW,
            first_slot=TrackerSlot(GeneratorName.TRIANGLE, SubColumn.VOLUME).flat_index,
            last_slot=TrackerSlot(GeneratorName.TRIANGLE, SubColumn.VOLUME).flat_index,
        )

    def test_a_menu_raised_with_nothing_selected_acts_on_the_clicked_cell(self) -> None:
        panel = _tracker_panel(Gestures())

        region = panel._menu_region(
            CLICKED_ROW,
            None,
            SubColumn.INSTRUMENT,
        )

        assert region.rows == range(CLICKED_ROW, CLICKED_ROW + 1)
        assert region.slots == (TrackerSlot(None, SubColumn.INSTRUMENT),)


class TestTrackerMenuItems:
    def test_the_items_hand_out_the_block_the_menu_was_raised_on(
        self,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        gestures = Gestures()
        panel = _tracker_panel(gestures)
        panel._input_state = _selected_tracker_state()
        selection = panel._input_state.region

        panel._add_block_items(CLICKED_ROW, GeneratorName.PULSE1, SubColumn.INSTRUMENT)
        for item in tracker_recorder.items:
            item.callback()

        assert gestures.copied == [selection]
        assert gestures.cut == [selection]
        assert gestures.deleted == [selection]

    def test_a_paste_anchors_at_the_clicked_cell(self, tracker_recorder: _MenuRecorder) -> None:
        """The cell carries a row and a column alone, so the clicked subcolumn is left to the block."""
        gestures = Gestures()
        panel = _tracker_panel(gestures)

        panel._add_block_items(CLICKED_ROW, GeneratorName.NOISE, SubColumn.VOLUME)
        tracker_recorder.items[PASTE_ITEM].callback()

        assert gestures.pasted == [TrackerCell(row=CLICKED_ROW, generator=GeneratorName.NOISE)]

    def test_paste_awaits_a_copy(self, tracker_recorder: _MenuRecorder) -> None:
        panel = _tracker_panel(Gestures(), can_paste=False)

        panel._add_block_items(CLICKED_ROW, GeneratorName.PULSE1, SubColumn.INSTRUMENT)

        assert tracker_recorder.items[PASTE_ITEM].enabled is False
        assert [item.enabled for item in tracker_recorder.items] == [True, True, False, True]

    def test_the_section_reads_as_the_four_clipboard_actions(
        self,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        panel = _tracker_panel(Gestures())

        panel._add_block_items(CLICKED_ROW, GeneratorName.PULSE1, SubColumn.INSTRUMENT)

        assert [item.label for item in tracker_recorder.items] == ["Copy", "Cut", "Paste", "Delete"]


class TestOrderMenuTarget:
    def test_a_menu_raised_inside_a_selection_acts_on_the_whole_of_it(self) -> None:
        panel = _order_panel(Gestures())
        panel._input_state = _selected_order_state()

        region = panel._menu_region(GeneratorName.PULSE1, CLICKED_POSITION + 1)

        assert region == panel._input_state.region

    def test_a_menu_raised_outside_a_selection_acts_on_the_clicked_cell(self) -> None:
        panel = _order_panel(Gestures())
        panel._input_state = _selected_order_state()

        region = panel._menu_region(None, CLICKED_POSITION)

        assert region == OrderRegion(
            first_row=CHANNEL_AXIS.index(None),
            last_row=CHANNEL_AXIS.index(None),
            first_position=CLICKED_POSITION,
            last_position=CLICKED_POSITION,
        )

    def test_a_menu_raised_with_nothing_selected_acts_on_the_clicked_cell(self) -> None:
        panel = _order_panel(Gestures())

        region = panel._menu_region(GeneratorName.PULSE1, CLICKED_POSITION)

        assert region == OrderRegion(
            first_row=PULSE1_ROW,
            last_row=PULSE1_ROW,
            first_position=CLICKED_POSITION,
            last_position=CLICKED_POSITION,
        )


class TestOrderMenuItems:
    def test_the_items_hand_out_the_block_the_menu_was_raised_on(
        self,
        order_recorder: _MenuRecorder,
    ) -> None:
        gestures = Gestures()
        panel = _order_panel(gestures)
        panel._input_state = _selected_order_state()
        selection = panel._input_state.region

        panel._add_block_items(GeneratorName.PULSE1, CLICKED_POSITION)
        for item in order_recorder.items:
            item.callback()

        assert gestures.copied == [selection]
        assert gestures.cut == [selection]
        assert gestures.deleted == [selection]

    def test_a_paste_anchors_at_the_clicked_cell(self, order_recorder: _MenuRecorder) -> None:
        gestures = Gestures()
        panel = _order_panel(gestures)

        panel._add_block_items(None, CLICKED_POSITION)
        order_recorder.items[PASTE_ITEM].callback()

        assert gestures.pasted == [OrderCell(generator=None, position=CLICKED_POSITION)]

    def test_paste_awaits_a_copy(self, order_recorder: _MenuRecorder) -> None:
        panel = _order_panel(Gestures(), can_paste=False)

        panel._add_block_items(GeneratorName.PULSE1, CLICKED_POSITION)

        assert order_recorder.items[PASTE_ITEM].enabled is False
        assert [item.enabled for item in order_recorder.items] == [True, True, False, True]

    def test_the_section_reads_as_the_four_clipboard_actions(
        self,
        order_recorder: _MenuRecorder,
    ) -> None:
        panel = _order_panel(Gestures())

        panel._add_block_items(GeneratorName.PULSE1, CLICKED_POSITION)

        assert [item.label for item in order_recorder.items] == ["Copy", "Cut", "Paste", "Delete"]


class TestMenuItemOrder:
    """The four items keep the order the indices name, which is what the item tests read them by."""

    def test_the_indices_name_the_items_they_stand_for(self, tracker_recorder: _MenuRecorder) -> None:
        panel = _tracker_panel(Gestures())

        panel._add_block_items(CLICKED_ROW, GeneratorName.PULSE1, SubColumn.INSTRUMENT)

        labels = [item.label for item in tracker_recorder.items]
        assert labels[COPY_ITEM] == "Copy"
        assert labels[CUT_ITEM] == "Cut"
        assert labels[PASTE_ITEM] == "Paste"
        assert labels[DELETE_ITEM] == "Delete"
