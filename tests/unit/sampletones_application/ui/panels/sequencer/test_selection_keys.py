from typing import List, Optional

import pytest

from sampletones_application.constants.sequencer import CHANNEL_AXIS
from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.view_model.sequencer.region import OrderRegion, TrackerRegion
from sampletones_application.view_model.sequencer.slot import SLOT_COUNT, TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.suite.shortcuts import shipped_source

ROW_COUNT = 64
POSITION_COUNT = 8
CURSOR_ROW = 4
CURSOR_POSITION = 2


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _tracker(
    channel: Optional[ChannelName] = ChannelName.PULSE1,
    subcolumn: SubColumn = SubColumn.INSTRUMENT,
) -> GUISequencerTrackerPanel:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(cursor=TrackerCursor(CURSOR_ROW, channel, subcolumn))
    panel._current_row_count = ROW_COUNT
    return panel


def _order(channel: Optional[ChannelName] = ChannelName.PULSE1) -> GUISequencerOrderPanel:
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = OrderInputState(cursor=OrderCursor(channel, CURSOR_POSITION))
    panel._position_count = POSITION_COUNT
    return panel


def _tracker_states(
    monkeypatch: pytest.MonkeyPatch,
    panel: GUISequencerTrackerPanel,
) -> List[TrackerInputState]:
    """The states a gesture applies, with the scroll a jump asks for left out."""
    states: List[TrackerInputState] = []
    monkeypatch.setattr(panel, "_apply_state", states.append)
    monkeypatch.setattr(panel, "_scroll_cursor_into_view", lambda: None)
    return states


def _order_states(
    monkeypatch: pytest.MonkeyPatch,
    panel: GUISequencerOrderPanel,
) -> List[OrderInputState]:
    states: List[OrderInputState] = []
    monkeypatch.setattr(panel, "_apply_state", states.append)
    return states


class TestTrackerSelectionKeys:
    """Shift held with a cursor key selects instead of moving, over the grid the cursor stands in."""

    def test_shift_down_selects_two_rows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Down")) is True
        assert states[-1].region == TrackerRegion(
            first_row=CURSOR_ROW,
            last_row=CURSOR_ROW + 1,
            first_slot=3,
            last_slot=3,
        )

    def test_shift_up_selects_the_row_above(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Up")) is True
        region = states[-1].region
        assert region is not None
        assert (region.first_row, region.last_row) == (CURSOR_ROW - 1, CURSOR_ROW)

    def test_shift_right_selects_the_next_subcolumn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Right")) is True
        region = states[-1].region
        assert region is not None
        assert region.slots == (
            TrackerSlot(ChannelName.PULSE1, SubColumn.INSTRUMENT),
            TrackerSlot(ChannelName.PULSE1, SubColumn.TRANSPOSE),
        )

    def test_shift_end_selects_to_the_last_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+End")) is True
        region = states[-1].region
        assert region is not None
        assert (region.first_row, region.last_row) == (CURSOR_ROW, ROW_COUNT - 1)

    def test_shift_home_selects_to_the_first_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Home")) is True
        region = states[-1].region
        assert region is not None
        assert (region.first_row, region.last_row) == (0, CURSOR_ROW)

    def test_a_plain_arrow_still_moves_the_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Down")) is True
        assert states[-1].region is None


class TestOrderSelectionKeys:
    """Shift held with a cursor key selects instead of moving, over the table the cursor stands in."""

    def test_shift_right_selects_two_positions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Right")) is True
        assert states[-1].region == OrderRegion(
            first_row=1,
            last_row=1,
            first_position=CURSOR_POSITION,
            last_position=CURSOR_POSITION + 1,
        )

    def test_shift_up_selects_up_to_the_master_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Up")) is True
        region = states[-1].region
        assert region is not None
        assert region.channels == (None, ChannelName.PULSE1)

    def test_shift_end_selects_to_the_last_position(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+End")) is True
        region = states[-1].region
        assert region is not None
        assert (region.first_position, region.last_position) == (CURSOR_POSITION, POSITION_COUNT - 1)

    def test_shift_home_selects_to_the_first_position(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Shift+Home")) is True
        region = states[-1].region
        assert region is not None
        assert (region.first_position, region.last_position) == (0, CURSOR_POSITION)

    def test_a_plain_arrow_still_moves_the_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Right")) is True
        assert states[-1].region is None


class TestTrackerSelectKeys:
    """The A chord selects a shape of the grid, each shape wider than the one Shift and Alt add."""

    def test_ctrl_a_selects_the_whole_frame(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+A")) is True
        region = states[-1].region
        assert region is not None
        assert (region.first_row, region.last_row) == (0, ROW_COUNT - 1)
        assert (region.first_slot, region.last_slot) == (0, SLOT_COUNT - 1)

    def test_ctrl_shift_a_selects_the_column_the_cursor_stands_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker(channel=ChannelName.TRIANGLE, subcolumn=SubColumn.VOLUME)
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+Shift+A")) is True
        region = states[-1].region
        assert region is not None
        assert region.slots == tuple(TrackerSlot(ChannelName.TRIANGLE, subcolumn) for subcolumn in SubColumn)

    def test_ctrl_alt_a_selects_the_subcolumn_the_cursor_stands_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _tracker(subcolumn=SubColumn.VOLUME)
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+Alt+A")) is True
        region = states[-1].region
        assert region is not None
        assert region.slots == (TrackerSlot(ChannelName.PULSE1, SubColumn.VOLUME),)

    def test_a_shape_stands_the_cursor_at_the_end_it_reaches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A Shift+Up straight after shrinks the selection from the row the shape ended on."""
        panel = _tracker()
        states = _tracker_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+A")) is True
        assert states[-1].cursor == TrackerCursor(ROW_COUNT - 1, ChannelName.NOISE, SubColumn.VOLUME)


class TestOrderSelectKeys:
    """The A chord selects a shape of the table, the whole order or the row the cursor stands in."""

    def test_ctrl_a_selects_the_whole_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+A")) is True
        region = states[-1].region
        assert region is not None
        assert region.channels == CHANNEL_AXIS
        assert (region.first_position, region.last_position) == (0, POSITION_COUNT - 1)

    def test_ctrl_shift_a_selects_the_row_the_cursor_stands_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order(channel=None)
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+Shift+A")) is True
        region = states[-1].region
        assert region is not None
        assert region.channels == (None,)
        assert (region.first_position, region.last_position) == (0, POSITION_COUNT - 1)

    def test_a_shape_stands_the_cursor_at_the_end_it_reaches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _order()
        states = _order_states(monkeypatch, panel)

        assert panel._on_key_pressed(_press("Ctrl+A")) is True
        assert states[-1].cursor == OrderCursor(CHANNEL_AXIS[-1], POSITION_COUNT - 1)
