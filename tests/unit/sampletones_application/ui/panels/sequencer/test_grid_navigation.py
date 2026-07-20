from types import SimpleNamespace
from typing import List

import pytest

from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.shortcuts.keys import KEY_PAGE_DOWN, KEY_PAGE_UP
from sampletones_application.view_model.sequencer.subcolumn import SubColumn

PAGE_SIZE = 16


def _panel() -> GUISequencerGridPanel:
    panel = GUISequencerGridPanel.__new__(GUISequencerGridPanel)
    panel._input_state = TrackerInputState(cursor=TrackerCursor(5, None, SubColumn.INSTRUMENT), pending="")
    panel._layout = SimpleNamespace(tracker=SimpleNamespace(page_size=PAGE_SIZE))
    return panel


class TestGridPageNavigation:
    """PageUp and PageDown jump the cursor a page of rows, matching the key codes DearPyGui delivers."""

    def test_page_up_moves_up_one_page(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        monkeypatch.setattr(panel, "_move_row", moves.append)

        assert panel._on_key_pressed(KeyEvent(key=KEY_PAGE_UP, ctrl=False, shift=False, alt=False)) is True
        assert moves == [-PAGE_SIZE]

    def test_page_down_moves_down_one_page(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        monkeypatch.setattr(panel, "_move_row", moves.append)

        assert panel._on_key_pressed(KeyEvent(key=KEY_PAGE_DOWN, ctrl=False, shift=False, alt=False)) is True
        assert moves == [PAGE_SIZE]
