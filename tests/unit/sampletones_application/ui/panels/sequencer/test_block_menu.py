import contextlib
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Iterator, List, Optional, Tuple

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer import order as order_module
from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures
from sampletones_application.ui.panels.sequencer.grid.surface import clipboard as clipboard_module
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.target import OrderTarget, TrackerTarget
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)
from sampletones_application.view_model.sequencer.slot import SLOT_COUNT, TrackerSlot, slot_from_flat
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.suite.grid import (
    ORDER_BLOCK_SHORTCUTS,
    TRACKER_BLOCK_SHORTCUTS,
    attach_edit_surface,
)
from tests.suite.shortcuts import shipped_source

CLICKED_ROW = 4
CLICKED_POSITION = 2
ROW_COUNT = 64
POSITION_COUNT = 8

COPY_ITEM = 0
CUT_ITEM = 1
PASTE_ITEM = 2
DELETE_ITEM = 3

SELECT_ALL_ITEM = 0
SELECT_COLUMN_ITEM = 1
SELECT_SUBCOLUMN_ITEM = 2
SELECT_ROW_ITEM = 1

PULSE1_ROW = CHANNEL_AXIS.index(ChannelName.PULSE1)


@dataclass
class MenuItem:
    """One item as it was registered, which is the whole of what a reader sees and clicks."""

    label: str
    enabled: bool
    callback: Callable[[], None]
    shortcut: str = ""


@dataclass
class Gestures:
    """What each block hook was handed when its menu item fired."""

    copied: List[Any] = field(default_factory=list)
    cut: List[Any] = field(default_factory=list)
    deleted: List[Any] = field(default_factory=list)
    pasted: List[Any] = field(default_factory=list)


def _prints_only() -> None:
    """Stands in for the callback of an item that only states something, such as an empty list."""


class _MenuRecorder:
    """Captures the items a builder registers, in the order it registers them."""

    def __init__(self) -> None:
        self.items: List[MenuItem] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(
            MenuItem(
                label=kwargs["label"],
                enabled=kwargs.get("enabled", True),
                callback=kwargs.get("callback", _prints_only),
                shortcut=kwargs.get("shortcut", ""),
            )
        )
        return 0


TRACKER_LABELS = (
    "select_all",
    "select_column",
    "select_subcolumn",
    "note_off",
    "set_instrument",
    "no_samples",
    "clear_subcolumn",
    "clear_cell",
    "clear_row",
)

ORDER_LABELS = (
    "select_all",
    "select_row",
    "duplicate",
    "clone",
    "insert",
    "clear",
    "remove",
    "move_left",
    "move_right",
    "move_start",
    "move_end",
)


def _labels(panel: Any, names: Tuple[str, ...]) -> None:
    """Gives the panel the words its own builders print, each reading as the action it names."""
    for name in names:
        setattr(panel, f"_lbl_context_{name}", name)


def _adjust_labels(panel: Any) -> None:
    """Gives the panel the words its transpose and volume items print, each reading as its element."""
    panel._lbl_adjust = {
        element: element.value for element, _, _ in (*tracker_module.TRANSPOSE_ACTIONS, *tracker_module.VOLUME_ACTIONS)
    }


def _tracker_panel(
    gestures: Gestures,
    *,
    can_paste: bool = True,
) -> tracker_module.GUISequencerTrackerPanel:
    """A tracker panel whose menu builder can run with no DearPyGui context behind it."""
    panel = tracker_module.GUISequencerTrackerPanel.__new__(tracker_module.GUISequencerTrackerPanel)
    _labels(panel, TRACKER_LABELS)
    _adjust_labels(panel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState()
    panel._current_samples = None
    panel.on_copy_block = gestures.copied.append
    panel.on_cut_block = gestures.cut.append
    panel.on_delete_block = gestures.deleted.append
    panel.on_paste_block = gestures.pasted.append
    panel.can_paste_block = lambda: can_paste
    panel._blocks = BlockGestures(grid=panel)
    attach_edit_surface(panel, TRACKER_BLOCK_SHORTCUTS, TrackerTarget)
    return panel


def _order_panel(
    gestures: Gestures,
    *,
    can_paste: bool = True,
) -> order_module.GUISequencerOrderPanel:
    """An order panel whose menu builder can run with no DearPyGui context behind it."""
    panel = order_module.GUISequencerOrderPanel.__new__(order_module.GUISequencerOrderPanel)
    _labels(panel, ORDER_LABELS)
    panel._shortcuts = shipped_source()
    panel._input_state = OrderInputState()
    panel._position_count = POSITION_COUNT
    panel.on_copy_block = gestures.copied.append
    panel.on_cut_block = gestures.cut.append
    panel.on_delete_block = gestures.deleted.append
    panel.on_paste_block = gestures.pasted.append
    panel.can_paste_block = lambda: can_paste
    panel._blocks = BlockGestures(grid=panel)
    attach_edit_surface(panel, ORDER_BLOCK_SHORTCUTS, OrderTarget)
    return panel


@contextlib.contextmanager
def _submenu(**_kwargs: Any) -> Iterator[None]:
    """Stands in for a submenu, whose items land in the same recording as the rest."""
    yield


def _record_into(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
) -> _MenuRecorder:
    recorder = _MenuRecorder()
    for target in (module, clipboard_module):
        monkeypatch.setattr(target.dpg, "add_menu_item", recorder.add_menu_item)
        monkeypatch.setattr(target.dpg, "add_separator", lambda **_kwargs: 0)
        monkeypatch.setattr(target.dpg, "menu", _submenu)

    return recorder


@pytest.fixture
def tracker_recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    return _record_into(monkeypatch, tracker_module)


@pytest.fixture
def order_recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    return _record_into(monkeypatch, order_module)


def _tracker_cell(channel: Optional[ChannelName]) -> TrackerCursor:
    """The clicked cell the tracker item tests raise their menu on."""
    return TrackerCursor(CLICKED_ROW, channel, SubColumn.INSTRUMENT)


def _order_cell(channel: Optional[ChannelName]) -> OrderCursor:
    """The clicked cell the order item tests raise their menu on."""
    return OrderCursor(channel, CLICKED_POSITION)


def _tracker_selections(
    monkeypatch: pytest.MonkeyPatch,
    panel: tracker_module.GUISequencerTrackerPanel,
) -> List[TrackerInputState]:
    """The states a select item applies, on a grid holding a cursor and the rows to reach."""
    panel._input_state = TrackerInputState(cursor=_tracker_cell(ChannelName.PULSE1))
    panel._current_row_count = ROW_COUNT
    states: List[TrackerInputState] = []
    monkeypatch.setattr(panel, "_apply_state", states.append)
    monkeypatch.setattr(panel, "_scroll_cursor_into_view", lambda: None)
    return states


def _order_selections(
    monkeypatch: pytest.MonkeyPatch,
    panel: order_module.GUISequencerOrderPanel,
) -> List[OrderInputState]:
    """The states a select item applies, on a table holding a cursor and the positions to reach."""
    panel._input_state = OrderInputState(cursor=_order_cell(ChannelName.PULSE1))
    states: List[OrderInputState] = []
    monkeypatch.setattr(panel, "_apply_state", lambda state, notify=True: states.append(state))
    return states


def _selected_tracker_state() -> TrackerInputState:
    """A selection running from the clicked row down two rows, over Pulse 1's whole cell."""
    state = TrackerInputState(cursor=TrackerCursor(CLICKED_ROW, ChannelName.PULSE1, SubColumn.INSTRUMENT))
    return state.extend_row(2, ROW_COUNT).extend_slot(2)


def _selected_order_state() -> OrderInputState:
    """A selection running from the clicked position across two positions of Pulse 1's row."""
    state = OrderInputState(cursor=OrderCursor(ChannelName.PULSE1, CLICKED_POSITION))
    return state.extend_position(2, POSITION_COUNT)


class TestTrackerTarget:
    def test_a_menu_raised_inside_a_selection_acts_on_the_whole_of_it(self) -> None:
        panel = _tracker_panel(Gestures())
        panel._input_state = _selected_tracker_state()

        target = panel._surface.target_at(
            TrackerCursor(
                CLICKED_ROW + 1,
                ChannelName.PULSE1,
                SubColumn.TRANSPOSE,
            )
        )

        assert target.region == panel._input_state.region

    def test_a_menu_raised_outside_a_selection_acts_on_the_clicked_cell(self) -> None:
        panel = _tracker_panel(Gestures())
        panel._input_state = _selected_tracker_state()

        target = panel._surface.target_at(
            TrackerCursor(
                CLICKED_ROW,
                ChannelName.TRIANGLE,
                SubColumn.VOLUME,
            )
        )

        assert target.region == TrackerRegion(
            first_row=CLICKED_ROW,
            last_row=CLICKED_ROW,
            first_slot=TrackerSlot(ChannelName.TRIANGLE, SubColumn.VOLUME).flat_index,
            last_slot=TrackerSlot(ChannelName.TRIANGLE, SubColumn.VOLUME).flat_index,
        )

    def test_a_menu_raised_with_nothing_selected_acts_on_the_clicked_cell(self) -> None:
        panel = _tracker_panel(Gestures())

        target = panel._surface.target_at(TrackerCursor(CLICKED_ROW, None, SubColumn.INSTRUMENT))

        assert target.region.rows == range(CLICKED_ROW, CLICKED_ROW + 1)
        assert target.region.slots == (TrackerSlot(None, SubColumn.INSTRUMENT),)

    def test_the_cursor_resolves_to_the_selection_it_ends(self) -> None:
        """The menu bar asks for the cursor's own target, which is the standing selection."""
        panel = _tracker_panel(Gestures())
        panel._input_state = _selected_tracker_state()

        target = panel._surface.cursor_target()

        assert target is not None
        assert target.region == panel._input_state.region

    def test_a_grid_holding_no_cursor_names_no_target(self) -> None:
        assert _tracker_panel(Gestures())._surface.cursor_target() is None

    def test_the_cursor_resolves_to_its_own_cell_with_nothing_selected(self) -> None:
        panel = _tracker_panel(Gestures())
        cursor = TrackerCursor(CLICKED_ROW, ChannelName.NOISE, SubColumn.VOLUME)
        panel._input_state = TrackerInputState(cursor=cursor)

        target = panel._surface.cursor_target()

        assert target is not None
        assert target.region == TrackerRegion(
            first_row=CLICKED_ROW,
            last_row=CLICKED_ROW,
            first_slot=TrackerSlot(ChannelName.NOISE, SubColumn.VOLUME).flat_index,
            last_slot=TrackerSlot(ChannelName.NOISE, SubColumn.VOLUME).flat_index,
        )
        assert target.anchor == TrackerCell(row=CLICKED_ROW, channel=ChannelName.NOISE)


class TestTrackerMenuItems:
    def test_the_items_hand_out_the_block_the_menu_was_raised_on(
        self,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        gestures = Gestures()
        panel = _tracker_panel(gestures)
        panel._input_state = _selected_tracker_state()
        selection = panel._input_state.region

        panel._surface.add_block_items(panel._surface.target_at(_tracker_cell(ChannelName.PULSE1)))
        for item in tracker_recorder.items:
            item.callback()

        assert gestures.copied == [selection]
        assert gestures.cut == [selection]
        assert gestures.deleted == [selection]

    def test_a_paste_anchors_at_the_clicked_cell(self, tracker_recorder: _MenuRecorder) -> None:
        """The cell carries a row and a column alone, so the clicked subcolumn is left to the block."""
        gestures = Gestures()
        panel = _tracker_panel(gestures)

        panel._surface.add_block_items(
            panel._surface.target_at(
                TrackerCursor(
                    CLICKED_ROW,
                    ChannelName.NOISE,
                    SubColumn.VOLUME,
                )
            )
        )
        tracker_recorder.items[PASTE_ITEM].callback()

        assert gestures.pasted == [TrackerCell(row=CLICKED_ROW, channel=ChannelName.NOISE)]

    def test_paste_awaits_a_copy(self, tracker_recorder: _MenuRecorder) -> None:
        panel = _tracker_panel(Gestures(), can_paste=False)

        panel._surface.add_block_items(panel._surface.target_at(_tracker_cell(ChannelName.PULSE1)))

        assert tracker_recorder.items[PASTE_ITEM].enabled is False
        assert [item.enabled for item in tracker_recorder.items] == [True, True, False, True]

    def test_the_section_reads_as_the_four_clipboard_actions(
        self,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        panel = _tracker_panel(Gestures())

        panel._surface.add_block_items(panel._surface.target_at(_tracker_cell(ChannelName.PULSE1)))

        assert [item.label for item in tracker_recorder.items] == ["Copy", "Cut", "Paste", "Delete"]


class TestOrderTarget:
    def test_a_menu_raised_inside_a_selection_acts_on_the_whole_of_it(self) -> None:
        panel = _order_panel(Gestures())
        panel._input_state = _selected_order_state()

        target = panel._surface.target_at(OrderCursor(ChannelName.PULSE1, CLICKED_POSITION + 1))

        assert target.region == panel._input_state.region

    def test_a_menu_raised_outside_a_selection_acts_on_the_clicked_cell(self) -> None:
        panel = _order_panel(Gestures())
        panel._input_state = _selected_order_state()

        target = panel._surface.target_at(_order_cell(None))

        assert target.region == OrderRegion(
            first_row=CHANNEL_AXIS.index(None),
            last_row=CHANNEL_AXIS.index(None),
            first_position=CLICKED_POSITION,
            last_position=CLICKED_POSITION,
        )

    def test_a_menu_raised_with_nothing_selected_acts_on_the_clicked_cell(self) -> None:
        panel = _order_panel(Gestures())

        target = panel._surface.target_at(_order_cell(ChannelName.PULSE1))

        assert target.region == OrderRegion(
            first_row=PULSE1_ROW,
            last_row=PULSE1_ROW,
            first_position=CLICKED_POSITION,
            last_position=CLICKED_POSITION,
        )

    def test_the_cursor_resolves_to_the_selection_it_ends(self) -> None:
        """The menu bar asks for the cursor's own target, which is the standing selection."""
        panel = _order_panel(Gestures())
        panel._input_state = _selected_order_state()

        target = panel._surface.cursor_target()

        assert target is not None
        assert target.region == panel._input_state.region

    def test_a_table_holding_no_cursor_names_no_target(self) -> None:
        assert _order_panel(Gestures())._surface.cursor_target() is None

    def test_the_cursor_resolves_to_its_own_cell_with_nothing_selected(self) -> None:
        panel = _order_panel(Gestures())
        cursor = OrderCursor(ChannelName.PULSE1, CLICKED_POSITION)
        panel._input_state = OrderInputState(cursor=cursor)

        target = panel._surface.cursor_target()

        assert target is not None
        assert target.region == OrderRegion(
            first_row=PULSE1_ROW,
            last_row=PULSE1_ROW,
            first_position=CLICKED_POSITION,
            last_position=CLICKED_POSITION,
        )
        assert target.anchor == OrderCell(channel=ChannelName.PULSE1, position=CLICKED_POSITION)


class TestOrderMenuItems:
    def test_the_items_hand_out_the_block_the_menu_was_raised_on(
        self,
        order_recorder: _MenuRecorder,
    ) -> None:
        gestures = Gestures()
        panel = _order_panel(gestures)
        panel._input_state = _selected_order_state()
        selection = panel._input_state.region

        panel._surface.add_block_items(panel._surface.target_at(_order_cell(ChannelName.PULSE1)))
        for item in order_recorder.items:
            item.callback()

        assert gestures.copied == [selection]
        assert gestures.cut == [selection]
        assert gestures.deleted == [selection]

    def test_a_paste_anchors_at_the_clicked_cell(self, order_recorder: _MenuRecorder) -> None:
        gestures = Gestures()
        panel = _order_panel(gestures)

        panel._surface.add_block_items(panel._surface.target_at(_order_cell(None)))
        order_recorder.items[PASTE_ITEM].callback()

        assert gestures.pasted == [OrderCell(channel=None, position=CLICKED_POSITION)]

    def test_paste_awaits_a_copy(self, order_recorder: _MenuRecorder) -> None:
        panel = _order_panel(Gestures(), can_paste=False)

        panel._surface.add_block_items(panel._surface.target_at(_order_cell(ChannelName.PULSE1)))

        assert order_recorder.items[PASTE_ITEM].enabled is False
        assert [item.enabled for item in order_recorder.items] == [True, True, False, True]

    def test_the_section_reads_as_the_four_clipboard_actions(
        self,
        order_recorder: _MenuRecorder,
    ) -> None:
        panel = _order_panel(Gestures())

        panel._surface.add_block_items(panel._surface.target_at(_order_cell(ChannelName.PULSE1)))

        assert [item.label for item in order_recorder.items] == ["Copy", "Cut", "Paste", "Delete"]


class TestActionSet:
    """One builder states each grid's actions, so every menu offering them prints the same set."""

    def test_the_tracker_action_set_leads_with_the_shapes_a_selection_takes(
        self,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        panel = _tracker_panel(Gestures())

        panel.add_action_items(panel._surface.target_at(_tracker_cell(ChannelName.PULSE1)))

        labels = [item.label for item in tracker_recorder.items]
        assert labels[:3] == ["select_all", "select_column", "select_subcolumn"]
        assert labels[3:7] == ["Copy", "Cut", "Paste", "Delete"]
        assert panel._lbl_context_clear_row in labels

    def test_the_order_action_set_leads_with_the_shapes_a_selection_takes(
        self,
        order_recorder: _MenuRecorder,
    ) -> None:
        panel = _order_panel(Gestures())

        panel.add_action_items(panel._surface.target_at(_order_cell(ChannelName.PULSE1)))

        labels = [item.label for item in order_recorder.items]
        assert labels[:2] == ["select_all", "select_row"]
        assert labels[2:6] == ["Copy", "Cut", "Paste", "Delete"]
        assert panel._lbl_context_move_end in labels


class TestMenuItemOrder:
    """The four items keep the order the indices name, which is what the item tests read them by."""

    def test_the_indices_name_the_items_they_stand_for(self, tracker_recorder: _MenuRecorder) -> None:
        panel = _tracker_panel(Gestures())

        panel._surface.add_block_items(panel._surface.target_at(_tracker_cell(ChannelName.PULSE1)))

        labels = [item.label for item in tracker_recorder.items]
        assert labels[COPY_ITEM] == "Copy"
        assert labels[CUT_ITEM] == "Cut"
        assert labels[PASTE_ITEM] == "Paste"
        assert labels[DELETE_ITEM] == "Delete"


class TestSelectItems:
    """The shapes each grid states, printed with their keys and firing what those keys fire."""

    def test_the_tracker_items_print_the_keys_they_answer(self, tracker_recorder: _MenuRecorder) -> None:
        panel = _tracker_panel(Gestures())

        panel._add_select_items(_tracker_cell(ChannelName.PULSE1))

        assert [item.shortcut for item in tracker_recorder.items] == [
            "Ctrl+A",
            "Ctrl+Shift+A",
            "Ctrl+Alt+A",
        ]

    def test_a_tracker_item_selects_the_column_the_menu_was_raised_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        """A menu names the cell it was raised on, so the shape reaches that cell's own column."""
        panel = _tracker_panel(Gestures())
        states = _tracker_selections(monkeypatch, panel)

        panel._add_select_items(_tracker_cell(ChannelName.TRIANGLE))
        tracker_recorder.items[SELECT_COLUMN_ITEM].callback()

        region = states[-1].region
        assert region is not None
        assert region.columns == (ChannelName.TRIANGLE,)
        assert (region.first_row, region.last_row) == (0, ROW_COUNT - 1)

    def test_a_tracker_item_selects_the_whole_frame(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tracker_recorder: _MenuRecorder,
    ) -> None:
        panel = _tracker_panel(Gestures())
        states = _tracker_selections(monkeypatch, panel)

        panel._add_select_items(_tracker_cell(ChannelName.TRIANGLE))
        tracker_recorder.items[SELECT_ALL_ITEM].callback()

        region = states[-1].region
        assert region is not None
        assert region.slots == tuple(slot_from_flat(index) for index in range(SLOT_COUNT))

    def test_the_order_items_print_the_keys_they_answer(self, order_recorder: _MenuRecorder) -> None:
        panel = _order_panel(Gestures())

        panel._add_select_items(_order_cell(ChannelName.PULSE1))

        assert [item.shortcut for item in order_recorder.items] == ["Ctrl+A", "Ctrl+Shift+A"]

    def test_an_order_item_selects_the_row_the_menu_was_raised_on(
        self,
        monkeypatch: pytest.MonkeyPatch,
        order_recorder: _MenuRecorder,
    ) -> None:
        panel = _order_panel(Gestures())
        states = _order_selections(monkeypatch, panel)

        panel._add_select_items(_order_cell(None))
        order_recorder.items[SELECT_ROW_ITEM].callback()

        region = states[-1].region
        assert region is not None
        assert region.channels == (None,)
        assert (region.first_position, region.last_position) == (0, POSITION_COUNT - 1)
