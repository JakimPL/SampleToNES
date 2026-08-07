from typing import Dict, Iterator, Optional
from unittest.mock import patch

import pytest

from sampletones_application.layout.general.caret import CaretLayout
from sampletones_application.ui.elements.table.caret import CaretOverlay
from sampletones_application.utils.palette.colors.written import LiteralColor

ROOT_WINDOW = "global.window.main"
ROOT_ID = 5
PANEL_WINDOW = "sequencer.panel.left"
PANEL_ID = 8
DIALOG_WINDOW = "global.dialog"
DIALOG_ID = 20

# Parent chains keyed by item id: the tracker's panel sits under the primary window,
# while the dialog is a top-level window outside it.
_PARENTS: Dict[int, Optional[int]] = {PANEL_ID: ROOT_ID, ROOT_ID: None, DIALOG_ID: None}
_ALIAS_IDS: Dict[str, int] = {ROOT_WINDOW: ROOT_ID, PANEL_WINDOW: PANEL_ID, DIALOG_WINDOW: DIALOG_ID}

CARET_LAYOUT = CaretLayout(
    fill=LiteralColor((102, 187, 255, 64)),
    border=LiteralColor((102, 187, 255, 255)),
    offset=3,
    width_padding=2,
)


@pytest.fixture(autouse=True)
def caret_state() -> Iterator[None]:
    CaretOverlay._root_window = ROOT_WINDOW
    CaretOverlay._layout = CARET_LAYOUT
    CaretOverlay._rectangle = 123
    CaretOverlay._widget = None
    yield
    CaretOverlay._root_window = None
    CaretOverlay._layout = None
    CaretOverlay._rectangle = None
    CaretOverlay._widget = None


def _alias_id(tag: str) -> int:
    return _ALIAS_IDS[tag]


def _parent(item: int) -> Optional[int]:
    return _PARENTS.get(item)


class TestActiveWithinRoot:
    def test_active_when_focus_sits_inside_the_root_tree(self) -> None:
        with patch("dearpygui.dearpygui.get_active_window", return_value=PANEL_ID):
            with patch("dearpygui.dearpygui.does_item_exist", return_value=True):
                with patch("dearpygui.dearpygui.get_alias_id", side_effect=_alias_id):
                    with patch("dearpygui.dearpygui.get_item_parent", side_effect=_parent):
                        assert CaretOverlay._active_within_root()

    def test_inactive_when_a_dialog_outside_the_tree_holds_focus(self) -> None:
        with patch("dearpygui.dearpygui.get_active_window", return_value=DIALOG_ID):
            with patch("dearpygui.dearpygui.does_item_exist", return_value=True):
                with patch("dearpygui.dearpygui.get_alias_id", side_effect=_alias_id):
                    with patch("dearpygui.dearpygui.get_item_parent", side_effect=_parent):
                        assert not CaretOverlay._active_within_root()

    def test_inactive_when_no_window_is_active(self) -> None:
        with patch("dearpygui.dearpygui.get_active_window", return_value=0):
            assert not CaretOverlay._active_within_root()

    def test_inactive_when_active_window_was_just_destroyed(self) -> None:
        stale_id = 3613
        with patch("dearpygui.dearpygui.get_active_window", return_value=stale_id):
            with patch("dearpygui.dearpygui.get_alias_id", side_effect=_alias_id):
                with patch("dearpygui.dearpygui.does_item_exist", return_value=False):
                    with patch("dearpygui.dearpygui.get_item_parent", side_effect=AssertionError("must not walk")):
                        assert not CaretOverlay._active_within_root()


class TestRedrawSuppression:
    def test_redraw_hides_the_box_when_focus_leaves_the_root_tree(self) -> None:
        with patch("dearpygui.dearpygui.get_active_window", return_value=DIALOG_ID):
            with patch("dearpygui.dearpygui.get_alias_id", side_effect=_alias_id):
                with patch("dearpygui.dearpygui.get_item_parent", side_effect=_parent):
                    with patch("dearpygui.dearpygui.does_item_exist", return_value=True):
                        with patch("dearpygui.dearpygui.configure_item") as configure:
                            CaretOverlay.redraw()

        configure.assert_called_once_with(123, show=False)
