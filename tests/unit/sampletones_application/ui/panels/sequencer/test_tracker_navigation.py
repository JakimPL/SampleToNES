from types import SimpleNamespace
from typing import List

import pytest

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.keyboard.keys import KEY_PAGE_DOWN, KEY_PAGE_UP
from sampletones_application.utils.gui.keyboard.modifiers import NO_MODIFIERS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn

PAGE_SIZE = 16


def _panel() -> GUISequencerTrackerPanel:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._input_state = TrackerInputState(cursor=TrackerCursor(5, None, SubColumn.INSTRUMENT), pending="")
    panel._layout = SimpleNamespace(tracker=SimpleNamespace(page_size=PAGE_SIZE))
    return panel


class TestGridPageNavigation:
    """PageUp and PageDown jump the cursor a page of rows, matching the key codes DearPyGui delivers,
    and reveal the row they land on."""

    def test_page_up_moves_up_one_page_and_scrolls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        scrolls: List[None] = []
        monkeypatch.setattr(panel, "_move_row", moves.append)
        monkeypatch.setattr(panel, "_scroll_cursor_into_view", lambda: scrolls.append(None))

        assert panel._on_key_pressed(KeyEvent(key=KEY_PAGE_UP, modifiers=NO_MODIFIERS)) is True
        assert moves == [-PAGE_SIZE]
        assert scrolls == [None]

    def test_page_down_moves_down_one_page_and_scrolls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        scrolls: List[None] = []
        monkeypatch.setattr(panel, "_move_row", moves.append)
        monkeypatch.setattr(panel, "_scroll_cursor_into_view", lambda: scrolls.append(None))

        assert panel._on_key_pressed(KeyEvent(key=KEY_PAGE_DOWN, modifiers=NO_MODIFIERS)) is True
        assert moves == [PAGE_SIZE]
        assert scrolls == [None]
