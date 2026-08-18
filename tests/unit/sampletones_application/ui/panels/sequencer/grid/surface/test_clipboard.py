from dataclasses import dataclass
from typing import Any, Callable, List

import pytest

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.ui.panels.sequencer.grid.surface import clipboard as clipboard_module
from tests.suite.grid import CLIPBOARD_LABELS, TRACKER_BLOCK_SHORTCUTS
from tests.suite.shortcuts import shipped_source
from tests.suite.surface import CLICKED_TARGET, Grid

COPY_ITEM = 0
CUT_ITEM = 1
PASTE_ITEM = 2
DELETE_ITEM = 3


@dataclass
class RecordedItem:
    """One item as it was registered, which is the whole of what a reader sees and clicks."""

    label: str
    shortcut: str
    enabled: bool
    callback: Callable[[], None]


class _MenuRecorder:
    def __init__(self) -> None:
        self.items: List[RecordedItem] = []

    def add_menu_item(self, **kwargs: Any) -> int:
        self.items.append(
            RecordedItem(
                label=kwargs["label"],
                shortcut=kwargs.get("shortcut", ""),
                enabled=kwargs.get("enabled", True),
                callback=kwargs["callback"],
            )
        )
        return 0


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _MenuRecorder:
    recorded = _MenuRecorder()
    monkeypatch.setattr(clipboard_module.dpg, "add_menu_item", recorded.add_menu_item)
    return recorded


class TestClipboardItems:
    def test_the_section_reads_as_the_four_clipboard_actions(self, recorder: _MenuRecorder) -> None:
        Grid().clipboard_items().add_items(CLICKED_TARGET)

        assert [item.label for item in recorder.items] == [
            CLIPBOARD_LABELS[ContextElements.COPY],
            CLIPBOARD_LABELS[ContextElements.CUT],
            CLIPBOARD_LABELS[ContextElements.PASTE],
            CLIPBOARD_LABELS[ContextElements.DELETE],
        ]

    def test_the_items_print_the_keys_the_grid_answers_to(self, recorder: _MenuRecorder) -> None:
        """Each grid states its own three bindings, and an item prints exactly the one it fires."""
        shortcuts = shipped_source()
        Grid().clipboard_items().add_items(CLICKED_TARGET)

        assert recorder.items[COPY_ITEM].shortcut == shortcuts.display(TRACKER_BLOCK_SHORTCUTS.copy)
        assert recorder.items[CUT_ITEM].shortcut == shortcuts.display(TRACKER_BLOCK_SHORTCUTS.cut)
        assert recorder.items[PASTE_ITEM].shortcut == shortcuts.display(TRACKER_BLOCK_SHORTCUTS.paste)

    def test_delete_prints_no_key_of_its_own(self, recorder: _MenuRecorder) -> None:
        """``Del`` empties a selection while one stands and clears the cell under the cursor
        otherwise, so the grid resolves it from the selection rather than from one binding."""
        Grid().clipboard_items().add_items(CLICKED_TARGET)

        assert recorder.items[DELETE_ITEM].shortcut == ""

    def test_the_items_act_on_the_block_they_were_raised_on(self, recorder: _MenuRecorder) -> None:
        """A menu item names its target when it is built, so it reaches that block wherever the
        cursor happens to stand."""
        grid = Grid()
        grid.clipboard_items().add_items(CLICKED_TARGET)

        for item in recorder.items:
            item.callback()

        assert grid.events == [
            f"copy {CLICKED_TARGET.region}",
            f"cut {CLICKED_TARGET.region}",
            f"paste {CLICKED_TARGET.anchor}",
            f"delete {CLICKED_TARGET.region}",
        ]

    def test_paste_awaits_a_copy(self, recorder: _MenuRecorder) -> None:
        Grid(can_paste=False).clipboard_items().add_items(CLICKED_TARGET)

        assert not recorder.items[PASTE_ITEM].enabled
        assert all(item.enabled for index, item in enumerate(recorder.items) if index != PASTE_ITEM)
