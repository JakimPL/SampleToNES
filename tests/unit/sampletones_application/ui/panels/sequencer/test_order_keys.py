from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_core.constants.enums import ChannelName
from tests.suite.shortcuts import shipped_source

POSITION_COUNT = 4
CURSOR_POSITION = 1

Move = Tuple[int, int]


@dataclass
class OrderPanelFixture:
    """A panel carrying the state the key path reads, with the calls each action makes recorded."""

    panel: GUISequencerOrderPanel
    inserted: List[int] = field(default_factory=list)
    duplicated: List[int] = field(default_factory=list)
    cloned: List[int] = field(default_factory=list)
    cleared: List[int] = field(default_factory=list)
    removed: List[int] = field(default_factory=list)
    moved: List[Move] = field(default_factory=list)
    entries: List[Tuple[int, Optional[int]]] = field(default_factory=list)
    states: List[OrderInputState] = field(default_factory=list)


@pytest.fixture
def order(monkeypatch: pytest.MonkeyPatch) -> OrderPanelFixture:
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = OrderInputState(cursor=OrderCursor(ChannelName.PULSE1, CURSOR_POSITION))
    panel._position_count = POSITION_COUNT
    panel._current_position = CURSOR_POSITION
    panel._buttons = None

    fixture = OrderPanelFixture(panel=panel)
    panel.on_insert_requested = fixture.inserted.append
    panel.on_duplicate_requested = fixture.duplicated.append
    panel.on_clone_requested = fixture.cloned.append
    panel.on_clear_requested = fixture.cleared.append
    panel.on_remove_requested = fixture.removed.append
    panel.on_move_requested = lambda position, target: fixture.moved.append((position, target))
    panel.on_set_order_entry = lambda _generator, position, index: fixture.entries.append((position, index))
    monkeypatch.setattr(panel, "_apply_state", fixture.states.append)
    return fixture


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestFrameActions:
    def test_the_duplicate_key_duplicates_the_cursor_frame(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Ctrl+Ins")) is True
        assert order.duplicated == [CURSOR_POSITION]
        assert order.cloned == []

    def test_the_clone_key_clones_the_cursor_frame(self, order: OrderPanelFixture) -> None:
        """Shift separates the two copies: the plain key repeats, the shifted one clones."""
        assert order.panel._on_key_pressed(_press("Ctrl+Shift+Ins")) is True
        assert order.cloned == [CURSOR_POSITION]
        assert order.duplicated == []

    def test_the_display_settings_key_reaches_the_application(self, order: OrderPanelFixture) -> None:
        """Ctrl+D belongs to the display settings now, so the table hands it to the shortcut scope."""
        assert order.panel._on_key_pressed(_press("Ctrl+D")) is False
        assert order.duplicated == []

    def test_the_insert_key_inserts_at_the_cursor(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("+")) is True
        assert order.inserted == [CURSOR_POSITION]

    def test_the_numeric_keypad_alias_inserts_the_same_way(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Num+")) is True
        assert order.inserted == [CURSOR_POSITION]

    def test_the_remove_key_removes_the_cursor_frame(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("-")) is True
        assert order.removed == [CURSOR_POSITION]

    def test_the_clear_frame_key_clears_the_whole_frame(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Shift+Del")) is True
        assert order.cleared == [CURSOR_POSITION]

    def test_the_add_key_inserts_after_the_cursor(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Ins")) is True
        assert order.inserted == [CURSOR_POSITION]


class TestFrameMoves:
    def test_the_move_left_key_moves_the_frame_one_position_back(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Alt+Left")) is True
        assert order.moved == [(CURSOR_POSITION, CURSOR_POSITION - 1)]

    def test_the_move_to_end_key_moves_the_frame_last(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Alt+End")) is True
        assert order.moved == [(CURSOR_POSITION, POSITION_COUNT - 1)]

    def test_a_move_with_nowhere_to_go_still_consumes_the_key(self, order: OrderPanelFixture) -> None:
        """A boundary keeps the press, so a repeated move stays out of the global shortcuts."""
        order.panel._input_state = OrderInputState(cursor=OrderCursor(ChannelName.PULSE1, 0))

        assert order.panel._on_key_pressed(_press("Alt+Left")) is True
        assert order.moved == []


class TestCursorMoves:
    def test_the_next_position_key_moves_the_cursor_one_column_on(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Right")) is True
        assert order.states[-1].cursor == OrderCursor(ChannelName.PULSE1, CURSOR_POSITION + 1)

    def test_the_enter_alias_moves_the_cursor_the_same_way(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Enter")) is True
        assert order.states[-1].cursor == OrderCursor(ChannelName.PULSE1, CURSOR_POSITION + 1)

    def test_the_last_position_key_jumps_to_the_final_column(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("End")) is True
        assert order.states[-1].cursor == OrderCursor(ChannelName.PULSE1, POSITION_COUNT - 1)


class TestCellEntry:
    def test_a_hex_key_types_into_the_cell_under_the_cursor(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("A")) is True
        assert order.states[-1].pending == "A"

    def test_a_modified_hex_key_reaches_the_application(self, order: OrderPanelFixture) -> None:
        """Ctrl+D opens the display settings, so cell entry keeps the plain key alone."""
        assert order.panel._on_key_pressed(_press("Ctrl+D")) is False
        assert order.states == []

    def test_the_clear_cell_key_empties_the_cell_and_moves_on(self, order: OrderPanelFixture) -> None:
        assert order.panel._on_key_pressed(_press("Del")) is True
        assert order.entries == [(CURSOR_POSITION, None)]

    def test_a_press_without_a_cursor_reaches_the_application(self, order: OrderPanelFixture) -> None:
        order.panel._input_state = OrderInputState(cursor=None)

        assert order.panel._on_key_pressed(_press("Right")) is False
