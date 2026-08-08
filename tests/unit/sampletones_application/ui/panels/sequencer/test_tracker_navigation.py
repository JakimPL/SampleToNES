from types import SimpleNamespace
from typing import List

import pytest

from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.keys import KEY_PAGE_DOWN, KEY_PAGE_UP
from sampletones_application.utils.gui.keyboard.modifiers import NO_MODIFIERS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from tests.suite.shortcuts import shipped_source

PAGE_SIZE = 16
CURSOR_ROW = 5


def _panel() -> GUISequencerTrackerPanel:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(
        cursor=TrackerCursor(CURSOR_ROW, None, SubColumn.INSTRUMENT),
        pending="",
    )
    panel._layout = SimpleNamespace(tracker=SimpleNamespace(page_size=PAGE_SIZE))
    return panel


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


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


class TestGridColumnNavigation:
    """Tab steps to the next channel column and Shift+Tab back, each its own action in the scheme."""

    def test_the_next_column_key_steps_forward(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        monkeypatch.setattr(panel, "_move_column", moves.append)

        assert panel._on_key_pressed(_press("Tab")) is True
        assert moves == [1]

    def test_the_previous_column_key_steps_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        monkeypatch.setattr(panel, "_move_column", moves.append)

        assert panel._on_key_pressed(_press("Shift+Tab")) is True
        assert moves == [-1]


class TestGridCellEntry:
    def test_a_note_key_types_into_the_cell_under_the_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        states: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", states.append)

        assert panel._on_key_pressed(_press("C")) is True
        assert states[-1].pending == "C"

    def test_a_modified_key_reaches_the_application(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ctrl+C carries no tracker action, so cell entry keeps the plain key alone."""
        panel = _panel()
        states: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", states.append)

        assert panel._on_key_pressed(_press("Ctrl+C")) is False
        assert states == []
