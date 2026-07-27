from typing import List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.order_input import OrderCursor, OrderInputState
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import NO_MODIFIERS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn


def _escape() -> KeyEvent:
    return KeyEvent(key=dpg.mvKey_Escape, modifiers=NO_MODIFIERS)


class TestGridEscapeYieldsToGlobalStop:
    """With no partial cell edit to cancel, the grid lets Escape fall through to global Stop."""

    def test_escape_yields_when_no_pending_edit(self) -> None:
        panel = GUISequencerGridPanel.__new__(GUISequencerGridPanel)
        panel._input_state = TrackerInputState(cursor=TrackerCursor(0, None, SubColumn.INSTRUMENT), pending="")

        assert panel._on_key_pressed(_escape()) is False

    def test_escape_cancels_a_pending_edit_and_consumes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = GUISequencerGridPanel.__new__(GUISequencerGridPanel)
        panel._input_state = TrackerInputState(cursor=TrackerCursor(0, None, SubColumn.INSTRUMENT), pending="3")
        applied: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", applied.append)

        assert panel._on_key_pressed(_escape()) is True
        assert applied and applied[0].pending == ""


class TestOrderEscapeYieldsToGlobalStop:
    """With no partial cell edit to cancel, the order table lets Escape fall through to global Stop."""

    def test_escape_yields_when_no_pending_edit(self) -> None:
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
        panel._input_state = OrderInputState(cursor=OrderCursor(None, 0), pending="")

        assert panel._on_key_pressed(_escape()) is False

    def test_escape_cancels_a_pending_edit_and_consumes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
        panel._input_state = OrderInputState(cursor=OrderCursor(None, 0), pending="3")
        applied: List[OrderInputState] = []
        monkeypatch.setattr(panel, "_apply_state", applied.append)

        assert panel._on_key_pressed(_escape()) is True
        assert applied and applied[0].pending == ""
