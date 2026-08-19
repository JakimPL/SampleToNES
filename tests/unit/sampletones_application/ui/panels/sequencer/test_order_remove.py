from dataclasses import dataclass, field
from typing import List, Optional

from sampletones_application.ui.panels.sequencer.input.order import (
    OrderCursor,
    OrderInputState,
)
from sampletones_application.ui.panels.sequencer.order import GUISequencerOrderPanel
from sampletones_core.constants.enums import ChannelName

POSITION_COUNT = 4


@dataclass
class ButtonsSpy:
    """Records the enabled state the panel pushes onto the ``[-]`` button."""

    states: List[bool] = field(default_factory=list)

    def set_decrement_enabled(self, enabled: bool) -> None:
        self.states.append(enabled)

    @property
    def enabled(self) -> Optional[bool]:
        return self.states[-1] if self.states else None


@dataclass
class OrderPanelFixture:
    panel: GUISequencerOrderPanel
    buttons: ButtonsSpy
    removed: List[int]


def _panel(
    *,
    cursor: Optional[OrderCursor] = None,
    current_position: Optional[int] = None,
    position_count: int = POSITION_COUNT,
) -> OrderPanelFixture:
    """A panel carrying only the state the removal path reads, bypassing the DearPyGui-dependent
    constructor."""
    panel = GUISequencerOrderPanel.__new__(GUISequencerOrderPanel)
    buttons = ButtonsSpy()
    removed: List[int] = []
    panel._buttons = buttons
    panel._input_state = OrderInputState(cursor=cursor)
    panel._current_position = current_position
    panel._position_count = position_count
    panel.on_remove_requested = removed.append
    return OrderPanelFixture(panel=panel, buttons=buttons, removed=removed)


class TestRemovableFrame:
    """The frame ``[-]`` acts on: the cursor's frame, else the followed tracker frame."""

    def test_cursor_frame_wins(self) -> None:
        fixture = _panel(cursor=OrderCursor(ChannelName.PULSE1, 2), current_position=0)

        assert fixture.panel._get_removable_position() == 2

    def test_followed_frame_answers_without_a_cursor(self) -> None:
        fixture = _panel(current_position=1)

        assert fixture.panel._get_removable_position() == 1

    def test_no_selection_resolves_to_nothing(self) -> None:
        fixture = _panel()

        assert fixture.panel._get_removable_position() is None

    def test_empty_order_resolves_to_nothing(self) -> None:
        fixture = _panel(current_position=0, position_count=0)

        assert fixture.panel._get_removable_position() is None

    def test_frame_past_the_end_resolves_to_nothing(self) -> None:
        fixture = _panel(current_position=POSITION_COUNT)

        assert fixture.panel._get_removable_position() is None


class TestRemoveButtonState:
    """``[-]`` is enabled exactly while a press would remove a frame."""

    def test_enabled_with_a_selected_frame(self) -> None:
        fixture = _panel(cursor=OrderCursor(None, 0))
        fixture.panel._refresh_remove_enabled()

        assert fixture.buttons.enabled is True

    def test_disabled_while_nothing_is_selected(self) -> None:
        fixture = _panel()
        fixture.panel._refresh_remove_enabled()

        assert fixture.buttons.enabled is False

    def test_disabled_on_an_empty_order(self) -> None:
        fixture = _panel(cursor=OrderCursor(None, 0), position_count=0)
        fixture.panel._refresh_remove_enabled()

        assert fixture.buttons.enabled is False


class TestRemoveClick:
    def test_click_removes_the_selected_frame(self) -> None:
        fixture = _panel(cursor=OrderCursor(ChannelName.NOISE, 3))
        fixture.panel._on_remove_clicked()

        assert fixture.removed == [3]

    def test_click_removes_the_followed_frame_without_a_cursor(self) -> None:
        fixture = _panel(current_position=2)
        fixture.panel._on_remove_clicked()

        assert fixture.removed == [2]

    def test_click_holds_still_while_nothing_is_selected(self) -> None:
        fixture = _panel()
        fixture.panel._on_remove_clicked()

        assert fixture.removed == []
