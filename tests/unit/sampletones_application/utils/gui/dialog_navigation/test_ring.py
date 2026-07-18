from typing import FrozenSet, List
from unittest.mock import MagicMock, patch

from sampletones_application.utils.gui.dialogs.ring import FocusRing
from sampletones_application.utils.gui.dialogs.stop import FocusStop

MODULE = "sampletones_application.utils.gui.dialog_navigation.ring"


def _dpg(
    *,
    focused: FrozenSet[str] = frozenset(),
    disabled: FrozenSet[str] = frozenset(),
) -> MagicMock:
    dpg = MagicMock()
    dpg.is_item_focused.side_effect = lambda tag: tag in focused
    dpg.is_item_enabled.side_effect = lambda tag: tag not in disabled
    return dpg


def _form_stops(cancel: MagicMock, ok: MagicMock) -> List[FocusStop]:
    return [
        FocusStop.field("title"),
        FocusStop.field("author"),
        FocusStop.field("comment"),
        FocusStop.button("cancel", cancel),
        FocusStop.button("ok", ok),
    ]


class TestCycle:
    def test_focus_initial_focuses_the_opening_stop(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=0)

        with patch(f"{MODULE}.dpg", _dpg()) as dpg:
            ring.focus_initial()

        dpg.focus_item.assert_called_once_with("title")

    def test_cycle_advances_to_the_next_stop(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=0)

        with patch(f"{MODULE}.dpg", _dpg()) as dpg:
            ring.cycle(1)

        dpg.focus_item.assert_called_once_with("author")

    def test_cycle_moves_backward(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=0)

        with patch(f"{MODULE}.dpg", _dpg()) as dpg:
            ring.cycle(-1)

        dpg.focus_item.assert_called_once_with("ok.button")

    def test_cycle_wraps_around(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg()) as dpg:
            ring.cycle(1)

        dpg.focus_item.assert_called_once_with("title")

    def test_cycle_skips_disabled_stops(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=2)

        with patch(f"{MODULE}.dpg", _dpg(disabled=frozenset({"cancel"}))) as dpg:
            ring.cycle(1)

        dpg.focus_item.assert_called_once_with("ok.button")

    def test_cycle_starts_from_the_clicked_field(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg(focused=frozenset({"author"}))) as dpg:
            ring.cycle(1)

        dpg.focus_item.assert_called_once_with("comment")


class TestActivateFocused:
    def test_activates_the_focused_button(self) -> None:
        cancel, ok = MagicMock(), MagicMock()
        ring = FocusRing(_form_stops(cancel, ok), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg()):
            ring.activate_focused()

        ok.assert_called_once_with()
        cancel.assert_not_called()

    def test_is_left_to_a_focused_field(self) -> None:
        cancel, ok = MagicMock(), MagicMock()
        ring = FocusRing(_form_stops(cancel, ok), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg(focused=frozenset({"comment"}))):
            ring.activate_focused()

        ok.assert_not_called()

    def test_ignores_a_disabled_button(self) -> None:
        cancel, ok = MagicMock(), MagicMock()
        ring = FocusRing(_form_stops(cancel, ok), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg(disabled=frozenset({"ok"}))):
            ring.activate_focused()

        ok.assert_not_called()
