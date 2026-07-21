from collections import defaultdict
from typing import Dict, FrozenSet, Generator, List
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_FOCUSED_BUTTON,
)
from sampletones_application.utils.gui.dialog_navigation.ring import FocusRing
from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop

MODULE = "sampletones_application.utils.gui.dialog_navigation.ring"


@pytest.fixture(autouse=True)
def _theme_registry() -> Generator[None, None, None]:
    with patch(f"{MODULE}.ThemeRegistry"):
        yield


def _dpg(
    *,
    active: FrozenSet[str] = frozenset(),
    disabled: FrozenSet[str] = frozenset(),
) -> MagicMock:
    dpg = MagicMock()
    dpg.is_item_active.side_effect = lambda tag: tag in active
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

    def test_cycle_starts_from_the_edited_field(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg(active=frozenset({"author"}))) as dpg:
            ring.cycle(1)

        dpg.focus_item.assert_called_once_with("comment")


class TestFocusOutline:
    def test_outlines_the_focused_button_and_restores_the_previous(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=3)

        themes: Dict[str, MagicMock] = defaultdict(MagicMock)
        registry = MagicMock()
        registry.get.side_effect = lambda tag: themes[tag]

        with patch(f"{MODULE}.dpg", _dpg()), patch(f"{MODULE}.ThemeRegistry", registry):
            ring.focus_initial()
            ring.cycle(1)

        themes[TAG_GLOBAL_THEME_FOCUSED_BUTTON].bind_to_item.assert_any_call("cancel.button")
        themes[TAG_GLOBAL_THEME_FOCUSED_BUTTON].bind_to_item.assert_any_call("ok.button")
        themes[TAG_GLOBAL_THEME_DEFAULT].bind_to_item.assert_any_call("cancel.button")

    def test_leaves_field_stops_without_an_outline(self) -> None:
        ring = FocusRing(_form_stops(MagicMock(), MagicMock()), initial_index=0)

        registry = MagicMock()

        with patch(f"{MODULE}.dpg", _dpg()), patch(f"{MODULE}.ThemeRegistry", registry):
            ring.focus_initial()
            ring.cycle(1)

        registry.get.assert_not_called()


class TestActivateFocused:
    def test_activates_the_focused_button(self) -> None:
        cancel, ok = MagicMock(), MagicMock()
        ring = FocusRing(_form_stops(cancel, ok), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg()):
            ring.activate_focused()

        ok.assert_called_once_with()
        cancel.assert_not_called()

    def test_is_left_to_the_edited_field(self) -> None:
        cancel, ok = MagicMock(), MagicMock()
        ring = FocusRing(_form_stops(cancel, ok), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg(active=frozenset({"comment"}))):
            ring.activate_focused()

        ok.assert_not_called()

    def test_ignores_a_disabled_button(self) -> None:
        cancel, ok = MagicMock(), MagicMock()
        ring = FocusRing(_form_stops(cancel, ok), initial_index=4)

        with patch(f"{MODULE}.dpg", _dpg(disabled=frozenset({"ok"}))):
            ring.activate_focused()

        ok.assert_not_called()
