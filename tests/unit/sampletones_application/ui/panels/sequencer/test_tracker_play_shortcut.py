from typing import List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import CTRL, CTRL_SHIFT
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from tests.suite.shortcuts import shipped_source


def _panel(cursor: Optional[TrackerCursor]) -> GUISequencerTrackerPanel:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(cursor=cursor, pending="")
    return panel


def _play_from_here() -> KeyEvent:
    return KeyEvent(key=dpg.mvKey_Spacebar, modifiers=CTRL_SHIFT)


class TestGridPlayFromHere:
    """Ctrl+Shift+Space plays from the cursor row; every other Ctrl press stays with the shortcuts."""

    def test_ctrl_shift_space_plays_from_the_cursor_row(self) -> None:
        rows: List[int] = []
        panel = _panel(TrackerCursor(5, None, SubColumn.INSTRUMENT))
        panel.on_play_from_row = rows.append

        assert panel._on_key_pressed(_play_from_here()) is True
        assert rows == [5]

    def test_ctrl_shift_space_yields_without_a_cursor(self) -> None:
        panel = _panel(None)

        assert panel._on_key_pressed(_play_from_here()) is False

    def test_ctrl_space_yields_to_the_global_shortcut(self) -> None:
        played: List[int] = []
        panel = _panel(TrackerCursor(5, None, SubColumn.INSTRUMENT))
        panel.on_play_from_row = played.append

        result = panel._on_key_pressed(KeyEvent(key=dpg.mvKey_Spacebar, modifiers=CTRL))

        assert result is False
        assert played == []
