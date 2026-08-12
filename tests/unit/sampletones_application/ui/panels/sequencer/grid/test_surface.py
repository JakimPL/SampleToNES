from dataclasses import dataclass
from typing import Any, Callable, Final, List, Optional, Tuple

import pytest

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.ui.panels.sequencer.grid import surface as surface_module
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures
from sampletones_application.ui.panels.sequencer.grid.surface import GridEditSurface
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.grid import CLIPBOARD_LABELS, TRACKER_BLOCK_SHORTCUTS
from tests.suite.shortcuts import shipped_source

CURSOR_CELL: Final[str] = "cursor cell"
CLICKED_CELL: Final[str] = "clicked cell"

COPY_ITEM = 0
CUT_ITEM = 1
PASTE_ITEM = 2
DELETE_ITEM = 3


@dataclass(frozen=True)
class _Target:
    """The cell a set of actions was raised on, and the block those actions act on."""

    cell: str
    region: str

    @property
    def anchor(self) -> str:
        return f"{self.cell} anchor"


@dataclass(frozen=True)
class _State:
    """A grid's state as the surface reads it: where the cursor stands, and what a cell falls in."""

    cursor: Optional[str]

    def region_at(self, cell: str) -> str:
        return f"{cell} block"


def _target_for(cell: str) -> _Target:
    return _Target(cell=cell, region=f"{cell} block")


CURSOR_TARGET: Final[_Target] = _target_for(CURSOR_CELL)
CLICKED_TARGET: Final[_Target] = _target_for(CLICKED_CELL)


class _Grid:
    """A grid recording what it was asked to do, in the order it was asked.

    The entry it settles, the hooks it announces through and the action sets it was asked to build
    land in one list, so a case reads both what a gesture reached and when the grid committed what
    was being typed.
    """

    def __init__(
        self,
        *,
        cursor: Optional[str] = CURSOR_CELL,
        owns: bool = True,
        can_paste: bool = True,
    ) -> None:
        self.events: List[str] = []
        self._cursor = cursor
        self._owns = owns
        self.on_copy_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"copy {region}")
        self.on_cut_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"cut {region}")
        self.on_delete_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"delete {region}")
        self.on_paste_block: Optional[Callable[[str], None]] = lambda cell: self.events.append(f"paste {cell}")
        self.can_paste_block: Optional[Callable[[], bool]] = lambda: can_paste

    def owns_keys(self) -> bool:
        return self._owns

    def input_state(self) -> _State:
        return _State(cursor=self._cursor)

    def add_action_items(self, target: _Target) -> None:
        self.events.append(f"actions {target.cell}")

    def commit_entry(self) -> None:
        self.events.append("commit")


def _surface(grid: _Grid) -> GridEditSurface[str, str, str, _Target]:
    return GridEditSurface(
        grid=grid,
        blocks=BlockGestures(grid=grid),
        target=_Target,
        shortcuts=shipped_source(),
        block_shortcuts=TRACKER_BLOCK_SHORTCUTS,
        labels=CLIPBOARD_LABELS,
    )


@dataclass(frozen=True)
class GestureCase:
    """One of the four gestures as a key press raises it, at the cursor's own target."""

    name: str
    at_cursor: Callable[[GridEditSurface[str, str, str, _Target]], None]
    reaches: str


CASES: Final[Tuple[GestureCase, ...]] = (
    GestureCase(
        name="copy",
        at_cursor=lambda surface: surface.copy(),
        reaches=f"copy {CURSOR_TARGET.region}",
    ),
    GestureCase(
        name="cut",
        at_cursor=lambda surface: surface.cut(),
        reaches=f"cut {CURSOR_TARGET.region}",
    ),
    GestureCase(
        name="delete",
        at_cursor=lambda surface: surface.delete(),
        reaches=f"delete {CURSOR_TARGET.region}",
    ),
    GestureCase(
        name="paste",
        at_cursor=lambda surface: surface.paste(),
        reaches=f"paste {CURSOR_TARGET.anchor}",
    ),
)


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
    monkeypatch.setattr(surface_module.dpg, "add_menu_item", recorded.add_menu_item)
    return recorded


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
class TestAtTheCursor:
    """A key press acts on the target the cursor names, once the entry being typed has landed."""

    def test_a_gesture_reaches_the_cursor_s_own_target(self, case: GestureCase) -> None:
        grid = _Grid()

        case.at_cursor(_surface(grid))

        assert grid.events == ["commit", case.reaches]

    def test_a_grid_holding_no_cursor_settles_its_entry_and_stands(self, case: GestureCase) -> None:
        grid = _Grid(cursor=None)

        case.at_cursor(_surface(grid))

        assert grid.events == ["commit"]


class TestEditActions:
    def test_the_cursor_names_the_target_the_actions_are_built_for(self) -> None:
        grid = _Grid()

        _surface(grid).build_edit_actions()

        assert grid.events == [f"actions {CURSOR_CELL}"]

    def test_a_grid_holding_no_cursor_builds_nothing(self) -> None:
        """The menu bar asks whichever grid answers, and one without a cursor states no actions."""
        grid = _Grid(cursor=None)

        _surface(grid).build_edit_actions()

        assert grid.events == []

    def test_a_grid_holding_no_cursor_names_no_target(self) -> None:
        assert _surface(_Grid(cursor=None)).cursor_target() is None

    def test_the_cursor_names_its_own_target(self) -> None:
        assert _surface(_Grid()).cursor_target() == CURSOR_TARGET

    def test_the_surface_answers_while_the_grid_owns_its_keys(self) -> None:
        """The menu offers what the next press would reach, so one question decides both."""
        assert _surface(_Grid(owns=True)).owns_edit_actions()
        assert not _surface(_Grid(owns=False)).owns_edit_actions()


class TestBlockItems:
    def test_the_section_reads_as_the_four_clipboard_actions(self, recorder: _MenuRecorder) -> None:
        _surface(_Grid()).add_block_items(CLICKED_TARGET)

        assert [item.label for item in recorder.items] == [
            CLIPBOARD_LABELS[ContextElements.COPY],
            CLIPBOARD_LABELS[ContextElements.CUT],
            CLIPBOARD_LABELS[ContextElements.PASTE],
            CLIPBOARD_LABELS[ContextElements.DELETE],
        ]

    def test_the_items_print_the_keys_the_grid_answers_to(self, recorder: _MenuRecorder) -> None:
        """Each grid states its own three bindings, and an item prints exactly the one it fires."""
        shortcuts = shipped_source()
        _surface(_Grid()).add_block_items(CLICKED_TARGET)

        assert recorder.items[COPY_ITEM].shortcut == shortcuts.display(ShortcutId.TRACKER_COPY_BLOCK)
        assert recorder.items[CUT_ITEM].shortcut == shortcuts.display(ShortcutId.TRACKER_CUT_BLOCK)
        assert recorder.items[PASTE_ITEM].shortcut == shortcuts.display(ShortcutId.TRACKER_PASTE_BLOCK)

    def test_delete_prints_no_key_of_its_own(self, recorder: _MenuRecorder) -> None:
        """``Del`` empties a selection while one stands and clears the cell under the cursor
        otherwise, so the grid resolves it from the selection rather than from one binding."""
        _surface(_Grid()).add_block_items(CLICKED_TARGET)

        assert recorder.items[DELETE_ITEM].shortcut == ""

    def test_the_items_act_on_the_block_they_were_raised_on(self, recorder: _MenuRecorder) -> None:
        """A menu item names its target when it is built, so it reaches that block wherever the
        cursor happens to stand."""
        grid = _Grid()
        _surface(grid).add_block_items(CLICKED_TARGET)

        for item in recorder.items:
            item.callback()

        assert grid.events == [
            f"copy {CLICKED_TARGET.region}",
            f"cut {CLICKED_TARGET.region}",
            f"paste {CLICKED_TARGET.anchor}",
            f"delete {CLICKED_TARGET.region}",
        ]

    def test_paste_awaits_a_copy(self, recorder: _MenuRecorder) -> None:
        _surface(_Grid(can_paste=False)).add_block_items(CLICKED_TARGET)

        assert not recorder.items[PASTE_ITEM].enabled
        assert all(item.enabled for index, item in enumerate(recorder.items) if index != PASTE_ITEM)
